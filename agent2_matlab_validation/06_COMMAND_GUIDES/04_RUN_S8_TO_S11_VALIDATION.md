# Run S8 to S11 Validation

Use the exact existing MATLAB scripts in the workspace:

```matlab
s8_stageA_verify
s8_stageB_verify
s8_stageC_verify
s9_stageA_verify
s9_stageB_verify
s9_stageC_verify
s10_combined_matlab_review_agent2
s11_combined_matlab_review_agent2
```

The repository also contains supporting probe and review files such as:
- `s10_combined_count_probe.m`
- `s11_combined_count_probe.m`

Expected report families:
- S8 Stage C MATLAB validation summaries
- S9 MATLAB validation summaries
- S10 MATLAB comparison summaries
- S11 MATLAB comparison summaries

The corresponding report-style evidence is already preserved in the workspace under the S8-S11 validation folder.
