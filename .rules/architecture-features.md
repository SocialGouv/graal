# Feature-Based Architecture

## Purpose
Feature modules in GRAAL amendment processing system (`graal/features/`)

## Must Do
- Implement `BaseFeature` interface from `graal/core/feature_interface.py`
- Maintain feature independence - no dependencies between features
- Support two-phase processing:
  - Phase 1: Sequential preprocessing (e.g., allotment filtering)
  - Phase 2: Parallel execution of enabled features
- Declare column ownership to prevent conflicts
- Support `no_value_overwrite` option to preserve existing values
- Handle errors gracefully - feature failure should not halt pipeline
- Enable/disable via YAML config
- Support allotment population (propagate to filtered amendments)
- Include concatenation support for comment columns when appropriate

## Must Not Do
- Create dependencies between features
- Modify columns owned by other features
- Assume specific execution order (except preprocessing phase)
- Block pipeline on non-critical errors
- Hardcode parameters (use YAML)

## Key Pattern
```python
class MyFeature(BaseFeature):
    def process(self, df):
        # Respect no_value_overwrite if configured
        if self.config.get('no_value_overwrite'):
            mask = df['column'].isna()
            df.loc[mask, 'column'] = values[mask]
        return df

```
