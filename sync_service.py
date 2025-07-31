import config
from datetime import datetime
from api_client import ApiClient
from excel_loader import ExcelLoader
from competency import Competency
from serializer import Serializer
from assigned_competency import AssignedCompetency
from hardcoded_rules import apply_medical_check_rule, should_assign_competency_based_on_dates

class CancelledByUserError(Exception):
    """Custom exception for when the user cancels an operation."""
    pass

class SyncService:
    def __init__(self, config):
        self.config = config
        self.api = ApiClient(config)
        self.excel_loader = ExcelLoader(config)

        # Data state
        self.mappings: list[tuple[str, str | Competency]] = []
        self.pilots: list[tuple[str, str, str]] = []
        self.account_map: dict[int, dict] = {}

    def load_excel_data(self, fpath, cancel_event=None):
        if cancel_event and cancel_event.is_set():
            raise CancelledByUserError("Operation cancelled by user.")
        self.excel_loader.load_excel(fpath)

        base_items = sorted({row["type"] for row in self.excel_loader.rows})
        source_items = []
        for item in base_items:
            source_items.append(f"{item} / date from")
            source_items.append(f"{item} / date to")

        if cancel_event and cancel_event.is_set():
            raise CancelledByUserError("Operation cancelled by user.")
        self.account_map = self.api.fetch_accounts_map()

        seen = set()
        pilots = []
        for i, row in enumerate(self.excel_loader.rows):
            if cancel_event and i % 50 == 0 and cancel_event.is_set():
                raise CancelledByUserError("Operation cancelled by user.")
            membership = int(row["membership"])
            name = row["name"]
            if membership not in seen:
                seen.add(membership)
                account = self.account_map.get(membership, {})
                pilot_id = account.get("id")
                pilots.append((name, membership, pilot_id))
        
        self.pilots = pilots
        return source_items, self.pilots

    def load_target_tree(self, cancel_event=None):
        if cancel_event and cancel_event.is_set():
            raise CancelledByUserError("Operation cancelled by user.")
        accounts = self.api.load_account_leaves()
        
        if cancel_event and cancel_event.is_set():
            raise CancelledByUserError("Operation cancelled by user.")
        competencies = self.api.load_competencies_subtree()
        tree = {}
        if accounts:
            tree["Accounts"] = accounts
        if competencies:
            tree["Competencies"] = competencies
        return tree
    
    def add_mapping(self, source_text, target_item, is_competency):
        if is_competency:
            # unsplit the source item
            if " / " in source_text:
                source_text = source_text[:source_text.rfind(" / ")]

        self.mappings.append((source_text, target_item))

    def get_mappings_for_display(self):
        display_list = []
        for source, target in self.mappings:
            if isinstance(target, Competency):
                target_label = target.path
            else:
                target_label = target
            display_list.append(f"{source} → {target_label}")
        return display_list

    def delete_mapping(self, index):
        if 0 <= index < len(self.mappings):
            del self.mappings[index]

    def save_mappings(self, path):
        Serializer.serialize(self.mappings, path)

    def load_mappings(self, path):
        self.mappings = Serializer.deserialize(path)
        
    def upload_data(self, check_only=False, log_callback=lambda msg, tag=None: None, cancel_event=None):
        successful_updates = 0
        for name, membership, _ in self.pilots:
            if cancel_event and cancel_event.is_set():
                raise CancelledByUserError("Operation cancelled by user.")

            account = self.account_map.get(int(membership))
            if not account:
                continue    
            pilot_id = account.get("id")
            if not pilot_id:
                continue

            matching_rows = [
                r for r in self.excel_loader.rows
                if str(r["membership"]) == str(membership)
            ]
            if not matching_rows:
                continue        

            successful_updates += self._upload_account_data(pilot_id, name, matching_rows, account.get("data", {}), check_only, log_callback, cancel_event)
            successful_updates += self._upload_competencies_data(pilot_id, name, matching_rows, check_only, log_callback, cancel_event)

        if check_only:
            log_callback("Check-only mode: no data was changed.", "info")
        elif successful_updates > 0:
            log_callback(f"Updated {successful_updates} items.", "success")
        else:
            log_callback("Data was already up to date, nothing changed.", "info")

        # reload accounts only if we updated something
        if not check_only and successful_updates > 0:
            self.account_map = self.api.fetch_accounts_map()
        
        return f"{'Compared' if check_only else 'Upload completed'}: {successful_updates} items {'would be' if check_only else 'were'} updated"

    def _upload_competencies_data(self, pilot_id, name, matching_rows, check_only, log_callback, cancel_event=None):
        successful_updates = 0
        pilot_current_competencies = None
        for excel_value_type, competency in self.mappings:
            if cancel_event and cancel_event.is_set():
                raise CancelledByUserError("Operation cancelled by user.")
            if not isinstance(competency, Competency):
                continue

            if pilot_current_competencies is None:
                pilot_current_competencies = self.api.get_competencies_by_pilot(pilot_id)

            row_type = excel_value_type # This was already unsplit
            row = next((r for r in matching_rows if r["type"] == row_type), None)
            if row is None:
                continue

            date_from, date_to = row["date from"], row["date to"]

            if should_assign_competency_based_on_dates(date_from, date_to):
                current_comp = pilot_current_competencies.get(competency.id)
                has_changed = not current_comp or current_comp.has_changed_compared_to_current(date_from, date_to)
                
                if has_changed:
                    if check_only:
                        log_callback(f"Would assign: {competency.name} to {name}", "info")
                        successful_updates += 1
                    else:
                        try:
                            self.api.assign_competency(pilot_id, competency.id, date_from, date_to)
                            log_callback(f"Assigned competency to pilot {name}: {competency.name}", "success")
                            successful_updates += 1
                        except Exception as e:
                            log_callback(f"Failed to assign competency {competency.name} to pilot {name}: {e}", "error")
            else: # should not be assigned
                if competency.id in pilot_current_competencies:
                    if check_only:
                        log_callback(f"Would revoke: {competency.name} from {name}", "info")
                        successful_updates += 1
                    else:
                        try:
                            self.api.revoke_competency(pilot_id, competency.id)
                            log_callback(f"Revoked competency from pilot {name}: {competency.name}", "warning")
                            successful_updates += 1
                        except Exception as e:
                            log_callback(f"Failed to revoke competency {competency.name} from pilot {name}: {e}", "error")
        return successful_updates

    def _upload_account_data(self, pilot_id, name, matching_rows, account_data, check_only, log_callback, cancel_event=None):
        updates = {}
        predefined_values_generators = {
            "Current DateTime": lambda: datetime.now().astimezone().isoformat(),
            "App Name (QualsSync)": lambda: config.APP_NAME
        }

        for excel_value_type, full_key in self.mappings:
            if cancel_event and cancel_event.is_set():
                raise CancelledByUserError("Operation cancelled by user.")
            if isinstance(full_key, Competency):
                continue

            field_name = full_key.split(" / ", 1)[1]
            
            if excel_value_type in predefined_values_generators:
                new_value = predefined_values_generators[excel_value_type]()
                if account_data.get(field_name) != new_value:
                    updates[field_name] = new_value
            else:
                row_type = excel_value_type.split(" / ", 1)[0]
                row_subtype_from_to = excel_value_type.split(" / ", 1)[1]
                for r in matching_rows:
                    if r["type"] != row_type:
                        continue
                    new_value = r.get(row_subtype_from_to)
                    if new_value is not None and account_data.get(field_name) != new_value:
                        updates[field_name] = new_value

        apply_medical_check_rule(updates, account_data, name, log_callback)

        if updates:
            if check_only:
                log_callback(f"Compared Pilot {name} - would update fields: {updates}", "info")
                return len(updates)
            else:
                try:
                    self.api.put_account_data(pilot_id, updates)
                    log_callback(f"Uploaded account data for pilot {name}: {updates}", "success")
                    return 1 # one successful update operation for this pilot
                except Exception as e:
                    log_callback(f"Failed to upload account data for pilot {name}", "error")
                    log_callback(f"  attempted updates: {updates}", "error")
                    log_callback(f"  error: {e}", "error")
                    return 0
        return 0
