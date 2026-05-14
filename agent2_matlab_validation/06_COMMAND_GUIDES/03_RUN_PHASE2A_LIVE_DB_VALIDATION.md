# Run Phase2A Live DB Validation

Preferred live validation command:

```matlab
cd('C:\Users\MSI\Desktop\2025 UH\Matlab')
startup
phase2a_live_db_validation_clean()
```

Legacy name that is still kept for reference:

```matlab
phase2a_live_db_validation()
```

If you need the old CSV-path validator for history only:

```matlab
phase2a_patch_validation()
```

Expected outputs:
- `PHASE2A_MATLAB_LIVE_DB_VALIDATION_REPORT.md`
- `phase2a_live_validation_output\`
- three selected PNG figures

Expected confirmed results from live DB validation:
- JDBC connection working: yes
- total DB runs visible: 1326
- S500 rows visible: 48
- S1000 rows visible: 48
- failed/partial Phase2A rows remaining: 0
- safe for report: yes

CSV package validation is skipped because live JDBC DB validation is available.
