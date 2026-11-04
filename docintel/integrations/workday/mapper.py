"""Configurable canonical-field to Workday-field mapping."""
class WorkdayFieldMapper:
    def __init__(self,field_map=None):
        self.field_map=field_map or {}
    def map_fields(self,extracted_data):
        mapped={}
        for canonical,workday_field in self.field_map.items():
            field=extracted_data.get(canonical)
            if field is not None:
                mapped[workday_field]=field.get("normalized_value") if field.get("normalized_value") is not None else field.get("value")
        return mapped
