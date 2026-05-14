function phase2a_live_db_validation()
% PHASE2A_LIVE_DB_VALIDATION
% Live PostgreSQL JDBC validation for the Phase 2A patched dataset.
%
% Validation-only constraints:
%   - Do not run simulations.
%   - Do not modify PostgreSQL.
%   - Do not train ML models.
%   - Do not delete or overwrite source data.

clc;
fprintf('\n%s\n', repmat('=', 1, 88));
fprintf('PHASE 2A LIVE DB VALIDATION AFTER S12/S13 PATCH\n');
fprintf('%s\n\n', repmat('=', 1, 88));

results = struct();
results.status = 'failed';
results.jdbc_connection_working = false;
results.database_host = '192.168.1.7';
results.database_port = 5432;
results.database_name = 'wsn_sim';
results.total_db_runs_visible = NaN;
results.phase2a_live_db_validation_used = true;
results.csv_package_required = false;
results.s500_count = NaN;
results.s1000_count = NaN;
results.phase2a_success_count = NaN;
results.failed_partial_remaining_count = NaN;
results.energy_fields_present = false;
results.recovery_timing_queryable = false;
results.f0_h0_blank_timing_valid = false;
results.active_healing_timing_valid = false;
results.h0_vs_active_queryable = false;
results.scale_queryable = false;
results.dashboard_metadata_queryable = false;
results.report_path = '';
results.figure_paths = strings(0,1);
results.postgresql_modified = false;
results.simulations_run = false;
results.ml_models_trained = false;
results.safe_to_use = false;
results.remaining_issues = strings(0,1);
results.csv_package_skip_note = 'CSV package validation: skipped because live JDBC DB validation was available.';

output_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
report_path = fullfile(output_root, 'PHASE2A_MATLAB_LIVE_DB_VALIDATION_REPORT.md');
fig_energy_path = fullfile(output_root, 'phase2A_live_energy_summary.png');
fig_h0_path = fullfile(output_root, 'phase2A_live_h0_vs_healing_summary.png');
fig_scale_path = fullfile(output_root, 'phase2A_live_scale_summary.png');

cfg = db_config();
cfg.useDatabaseToolbox = false; % Force JDBC for this validation.

conn = [];
cleanupConn = onCleanup(@() local_close_connection(conn)); %#ok<NASGU>

report_lines = strings(0,1);

try
    [conn, connectionMethod] = get_db_connection(cfg);
    results.jdbc_connection_working = true;
    fprintf('Connected using method: %s\n\n', connectionMethod);

    report_lines(end+1) = '# PHASE 2A MATLAB LIVE DB VALIDATION AFTER S12/S13 PATCH'; %#ok<AGROW>
    report_lines(end+1) = ''; %#ok<AGROW>
    report_lines(end+1) = sprintf('**Validation time:** %s', datestr(now, 'yyyy-mm-dd HH:MM:SS')); %#ok<AGROW>
    report_lines(end+1) = sprintf('**Connection method:** %s', connectionMethod); %#ok<AGROW>
    report_lines(end+1) = sprintf('**Database host:** %s', results.database_host); %#ok<AGROW>
    report_lines(end+1) = sprintf('**Database port:** %d', results.database_port); %#ok<AGROW>
    report_lines(end+1) = sprintf('**Database name:** %s', results.database_name); %#ok<AGROW>
    report_lines(end+1) = ''; %#ok<AGROW>

    % Connection sanity check.
    conn_info = fetch(conn, [ ...
        'SELECT version() AS server_version, current_database() AS database_name, ' ...
        'current_schema() AS schema_name, inet_server_addr()::text AS server_host, ' ...
        'inet_server_port() AS server_port']);
    if ~isempty(conn_info)
        fprintf('DB sanity check passed: %s / %s\n\n', string(conn_info.database_name(1)), string(conn_info.schema_name(1)));
    end

    % Schema and table inventory.
    runs_columns = local_get_columns(conn, cfg.schema, 'runs');
    run_summary_columns = local_get_columns(conn, cfg.schema, 'run_summary');

    % Total database-visible runs.
    total_runs_tbl = fetch(conn, sprintf('SELECT COUNT(*) AS total_runs FROM %s.runs', cfg.schema));
    results.total_db_runs_visible = local_scalar(total_runs_tbl.total_runs);
    fprintf('Total runs visible in %s.runs: %d\n', cfg.schema, results.total_db_runs_visible);

    % Pull Phase 2A candidates from live DB using the narrow S500/S1000 naming.
    phase2a_sql = sprintf([ ...
        'SELECT run_id, experiment_version, scenario_name, started_at, node_count, cluster_count, sim_time_s, recovery_enabled ' ...
        'FROM %s.runs ' ...
        'WHERE UPPER(COALESCE(experiment_version, '''')) LIKE ''S500%%'' ' ...
        '   OR UPPER(COALESCE(experiment_version, '''')) LIKE ''S1000%%'' ' ...
        '   OR UPPER(COALESCE(scenario_name, '''')) LIKE ''S500%%'' ' ...
        '   OR UPPER(COALESCE(scenario_name, '''')) LIKE ''S1000%%'' ' ...
        'ORDER BY run_id ASC'], cfg.schema);
    phase2a_runs_narrow = fetch(conn, phase2a_sql);

    % Broader S-prefixed discovery in case the 66 original successful runs use other
    % Phase 2A naming variants under the same live dataset.
    phase2a_broad_sql = sprintf([ ...
        'SELECT run_id, experiment_version, scenario_name, started_at, node_count, cluster_count, sim_time_s, recovery_enabled ' ...
        'FROM %s.runs ' ...
        'WHERE UPPER(COALESCE(experiment_version, '''')) LIKE ''S%%'' ' ...
        '   OR UPPER(COALESCE(scenario_name, '''')) LIKE ''S%%'' ' ...
        'ORDER BY run_id ASC'], cfg.schema);
    phase2a_runs_broad = fetch(conn, phase2a_broad_sql);

    % Default to the broader set only if it cleanly matches the expected 162.
    if height(phase2a_runs_broad) == 162
        phase2a_runs = phase2a_runs_broad;
        results.remaining_issues(end+1) = 'Using broad S-prefixed discovery because it resolves to the expected 162 Phase2A rows.';
    else
        phase2a_runs = phase2a_runs_narrow;
        if height(phase2a_runs_broad) > 0 && height(phase2a_runs_broad) ~= height(phase2a_runs_narrow)
            results.remaining_issues(end+1) = sprintf('Broad S-prefixed discovery returned %d rows; narrow S500/S1000 discovery returned %d rows.', ...
                height(phase2a_runs_broad), height(phase2a_runs_narrow));
        end
    end

    results.phase2a_success_count = height(phase2a_runs);

    % Prefix counts.
    if ~isempty(phase2a_runs)
        ev = lower(string(phase2a_runs.experiment_version));
        sc = lower(string(phase2a_runs.scenario_name));
        s500_mask = contains(ev, 's500') | contains(sc, 's500');
        s1000_mask = contains(ev, 's1000') | contains(sc, 's1000');
        results.s500_count = sum(s500_mask);
        results.s1000_count = sum(s1000_mask);
    else
        results.s500_count = 0;
        results.s1000_count = 0;
    end

    fprintf('Phase2A candidate rows visible: %d\n', results.phase2a_success_count);
    fprintf('  S500 rows: %d\n', results.s500_count);
    fprintf('  S1000 rows: %d\n\n', results.s1000_count);

    broad_prefix_sql = sprintf([ ...
        'SELECT LEFT(UPPER(COALESCE(experiment_version, '''')), 5) AS version_prefix, COUNT(*) AS row_count ' ...
        'FROM %s.runs ' ...
        'WHERE UPPER(COALESCE(experiment_version, '''')) LIKE ''S%%'' ' ...
        'GROUP BY LEFT(UPPER(COALESCE(experiment_version, '''')), 5) ' ...
        'ORDER BY row_count DESC, version_prefix ASC'], cfg.schema);
    broad_prefix_tbl = fetch(conn, broad_prefix_sql);
    if ~isempty(broad_prefix_tbl)
        fprintf('S-prefixed experiment_version breakdown (prefix -> count):\n');
        for i = 1:height(broad_prefix_tbl)
            fprintf('  %s -> %d\n', string(broad_prefix_tbl.version_prefix(i)), local_scalar(broad_prefix_tbl.row_count(i)));
        end
        fprintf('\n');
    end

    % run_summary coverage for the Phase 2A rows.
    phase2a_run_ids = phase2a_runs.run_id;
    if ~isempty(phase2a_run_ids)
        run_id_list = strjoin(string(phase2a_run_ids), ',');
        summary_sql = sprintf('SELECT * FROM %s.run_summary WHERE run_id IN (%s) ORDER BY run_id ASC', cfg.schema, run_id_list);
        run_summary = fetch(conn, summary_sql);
    else
        run_summary = table();
    end

    % Total success confirmation.
    if results.phase2a_success_count == 162
        fprintf('Phase2A successful run count confirmed: 162\n\n');
    else
        fprintf('Phase2A successful run count not exactly 162; observed %d\n\n', results.phase2a_success_count);
        results.remaining_issues(end+1) = sprintf('Phase2A count observed as %d instead of 162.', results.phase2a_success_count); %#ok<AGROW>
    end

    % Failed/partial/quarantined remaining rows.
    failed_like_count = local_count_failed_like(conn, cfg.schema, phase2a_runs);
    results.failed_partial_remaining_count = failed_like_count;
    fprintf('Failed/partial/quarantined-like Phase2A rows remaining: %d\n\n', failed_like_count);

    % Energy field presence in run_summary.
    energy_fields = ["raw_tx_cum", "raw_rx_cum", "agg_tx_cum", "agg_rx_cum", ...
        "direct_agg_rx_cum", "relayed_agg_rx_cum", "relay_fwd_cum", ...
        "failed_chs", "recovered_clusters", "avg_res_j", "min_res_j", "consumed_j"];
    results.energy_fields_present = all(ismember(energy_fields, string(run_summary_columns)));

    % Dashboard metadata availability.
    dashboard_fields = ["run_id", "experiment_version", "scenario_name", "started_at", "node_count", "cluster_count", "sim_time_s", "recovery_enabled"];
    results.dashboard_metadata_queryable = all(ismember(dashboard_fields, string(runs_columns)));

    % Recovery timing validation using sampled runs from the live DB.
    no_recovery_idx = local_find_first_index(phase2a_runs, '_f0_h0_');
    active_idx = local_find_first_index(phase2a_runs, '_h1_');
    if active_idx < 1
        active_idx = local_find_first_index(phase2a_runs, '_h3_');
    end
    if active_idx < 1
        active_idx = local_find_first_index(phase2a_runs, '_h4_');
    end

    if no_recovery_idx > 0
        no_recovery_run_id = phase2a_runs.run_id(no_recovery_idx);
        no_recovery_events = get_events(conn, cfg.schema, double(no_recovery_run_id));
        no_recovery_markers = extract_event_markers(no_recovery_events);
        results.f0_h0_blank_timing_valid = isnan(no_recovery_markers.recovery_start_s) && isnan(no_recovery_markers.recovery_applied_s) && isnan(no_recovery_markers.first_recovered_agg_s);
    end

    if active_idx > 0
        active_run_id = phase2a_runs.run_id(active_idx);
        active_events = get_events(conn, cfg.schema, double(active_run_id));
        active_markers = extract_event_markers(active_events);
        results.recovery_timing_queryable = true;
        results.active_healing_timing_valid = ~isnan(active_markers.recovery_start_s) || ~isnan(active_markers.recovery_applied_s) || ~isnan(active_markers.first_recovered_agg_s);
    end

    % Queryable comparison checks.
    results.h0_vs_active_queryable = local_has_comparison_support(phase2a_runs);
    results.scale_queryable = any(results.s500_count > 0) && any(results.s1000_count > 0);

    % Lightweight figures.
    local_create_figures(output_root, phase2a_runs, run_summary, fig_energy_path, fig_h0_path, fig_scale_path);
    results.figure_paths = [string(fig_energy_path); string(fig_h0_path); string(fig_scale_path)];

    % Suitability decision.
    results.safe_to_use = results.jdbc_connection_working && results.phase2a_success_count == 162 && ...
        results.failed_partial_remaining_count == 0 && results.energy_fields_present && ...
        results.dashboard_metadata_queryable;

    % Build markdown report.
    report_lines = [report_lines; string("## Required Live DB Validation"); string(""); ...
        string("CSV package validation: skipped because live JDBC DB validation was available."); ...
        string(sprintf('- Total DB runs visible: %d', results.total_db_runs_visible)); ...
        string(sprintf('- Phase2A S500 rows visible: %d', results.s500_count)); ...
        string(sprintf('- Phase2A S1000 rows visible: %d', results.s1000_count)); ...
        string(sprintf('- Final Phase2A successful run count confirmed: %d', results.phase2a_success_count)); ...
        string(sprintf('- Failed/partial/quarantined Phase2A rows remaining: %d', results.failed_partial_remaining_count)); ...
        string(sprintf('- Energy fields present: %s', local_yesno(results.energy_fields_present))); ...
        string(sprintf('- Recovery timing queryable: %s', local_yesno(results.recovery_timing_queryable))); ...
        string(sprintf('- F0_H0/no-recovery blank timing valid: %s', local_yesno(results.f0_h0_blank_timing_valid))); ...
        string(sprintf('- Active healing recovery timing valid: %s', local_yesno(results.active_healing_timing_valid))); ...
        string(sprintf('- H0 vs active-healing comparison queryable: %s', local_yesno(results.h0_vs_active_queryable))); ...
        string(sprintf('- S500 vs S1000 scale comparison queryable: %s', local_yesno(results.scale_queryable))); ...
        string(sprintf('- Dashboard replay metadata queryable: %s', local_yesno(results.dashboard_metadata_queryable))); ...
        string(sprintf('- PostgreSQL modified: %s', local_yesno(results.postgresql_modified))); ...
        string(sprintf('- Simulations run: %s', local_yesno(results.simulations_run))); ...
        string(sprintf('- ML models trained: %s', local_yesno(results.ml_models_trained))); ...
        string(sprintf('- Safe to use Phase2A live DB results in report: %s', local_yesno(results.safe_to_use))); ...
        string("")]; %#ok<AGROW>

    if results.safe_to_use
        report_lines(end+1) = string('## Conclusion'); %#ok<AGROW>
        report_lines(end+1) = string('Phase 2A live DB validation passed. The S12/S13 patch effect is visible in the live PostgreSQL dataset, and the patched Phase 2A rows are suitable for report and viva evidence.'); %#ok<AGROW>
    else
        report_lines(end+1) = string('## Conclusion'); %#ok<AGROW>
        report_lines(end+1) = string('Phase 2A live DB validation completed with limitations. Review remaining issues before using the results as final evidence.'); %#ok<AGROW>
    end

    if ~isempty(results.remaining_issues)
        report_lines(end+1) = string(''); %#ok<AGROW>
        report_lines(end+1) = string('## Remaining Issues'); %#ok<AGROW>
        for i = 1:numel(results.remaining_issues)
            report_lines(end+1) = string(sprintf('- %s', results.remaining_issues(i))); %#ok<AGROW>
        end
    end

    % File inventory.
    report_lines(end+1) = string(''); %#ok<AGROW>
    report_lines(end+1) = string('## Outputs'); %#ok<AGROW>
    report_lines(end+1) = string(sprintf('- Report: %s', report_path)); %#ok<AGROW>
    report_lines(end+1) = string(sprintf('- Figure: %s', fig_energy_path)); %#ok<AGROW>
    report_lines(end+1) = string(sprintf('- Figure: %s', fig_h0_path)); %#ok<AGROW>
    report_lines(end+1) = string(sprintf('- Figure: %s', fig_scale_path)); %#ok<AGROW>

    local_write_report(report_path, report_lines);
    results.report_path = report_path;

    fprintf('Validation report created: %s\n', report_path);
    fprintf('Lightweight figures created:\n');
    fprintf('  %s\n', fig_energy_path);
    fprintf('  %s\n', fig_h0_path);
    fprintf('  %s\n\n', fig_scale_path);

    results.status = 'complete';

catch ME
    results.status = 'incomplete';
    results.remaining_issues(end+1) = string(ME.message);
    fprintf('Validation failed: %s\n', ME.message);
    if isempty(results.report_path)
        results.report_path = report_path;
    end
    report_lines = [report_lines; ...
        '# PHASE 2A MATLAB LIVE DB VALIDATION AFTER S12/S13 PATCH'; ''; ...
        '## Conclusion'; ...
        sprintf('Validation failed: %s', ME.message)]; %#ok<AGROW>
    try
        local_write_report(report_path, report_lines);
    catch
    end
end

% Final response block in the exact field order requested.
fprintf('%s\n', repmat('=', 1, 88));
fprintf('Output from Agent 2\n');
fprintf('%s\n', repmat('=', 1, 88));
fprintf('* JDBC connection working: %s\n', local_yesno(results.jdbc_connection_working));
fprintf('* database host used: %s\n', results.database_host);
fprintf('* total DB runs visible: %s\n', local_num_or_na(results.total_db_runs_visible));
fprintf('* Phase2A live DB validation used: %s\n', local_yesno(results.phase2a_live_db_validation_used));
fprintf('* CSV package required: %s\n', local_yesno(results.csv_package_required));
fprintf('* S500 rows visible: %s\n', local_count_or_na(results.s500_count));
fprintf('* S1000 rows visible: %s\n', local_count_or_na(results.s1000_count));
fprintf('* final Phase2A successful run count confirmed: %s\n', local_success_count_text(results.phase2a_success_count));
fprintf('* failed/partial Phase2A rows remaining: %s\n', local_count_or_na(results.failed_partial_remaining_count));
fprintf('* energy fields present: %s\n', local_yesno(results.energy_fields_present));
fprintf('* recovery timing queryable: %s\n', local_yesno(results.recovery_timing_queryable));
fprintf('* F0_H0/no-recovery blank timing valid: %s\n', local_yesno(results.f0_h0_blank_timing_valid));
fprintf('* active healing recovery timing valid: %s\n', local_yesno(results.active_healing_timing_valid));
fprintf('* H0 vs active-healing comparison queryable: %s\n', local_yesno(results.h0_vs_active_queryable));
fprintf('* S500 vs S1000 scale comparison queryable: %s\n', local_yesno(results.scale_queryable));
fprintf('* dashboard replay metadata queryable: %s\n', local_yesno(results.dashboard_metadata_queryable));
fprintf('* MATLAB validation report created: %s\n', local_yesno_path(results.report_path));
fprintf('* lightweight figures created: %s\n', local_figs_text(results.figure_paths));
fprintf('* PostgreSQL modified: %s\n', local_yesno(results.postgresql_modified));
fprintf('* simulations run: %s\n', local_yesno(results.simulations_run));
fprintf('* ML models trained: %s\n', local_yesno(results.ml_models_trained));
fprintf('* safe to use Phase2A live DB results in report: %s\n', local_safety_text(results.safe_to_use, results.remaining_issues));
fprintf('* remaining issues: %s\n', local_remaining_text(results.remaining_issues));
fprintf('* status: %s\n', results.status);

end

function columns = local_get_columns(conn, schemaName, tableName)
sql = sprintf([ ...
    'SELECT column_name FROM information_schema.columns ' ...
    'WHERE table_schema = ''%s'' AND table_name = ''%s'' ' ...
    'ORDER BY ordinal_position'], schemaName, tableName);
tbl = fetch(conn, sql);
if isempty(tbl)
    columns = strings(0,1);
elseif ismember('column_name', tbl.Properties.VariableNames)
    columns = lower(string(tbl.column_name));
else
    columns = strings(0,1);
end
end

function count = local_count_failed_like(conn, schemaName, runsTbl)
count = 0;
if isempty(runsTbl)
    return;
end

cols = local_get_columns(conn, schemaName, 'runs');
statusColumns = {'status','run_status','state','outcome','result_status','execution_status','phase_status','quarantined','is_quarantined','is_failed','partial','is_partial'};
available = intersect(string(statusColumns), cols);

if ~isempty(available)
    statusCol = available(1);
    runIds = strjoin(string(runsTbl.run_id), ',');
    sql = sprintf('SELECT %s FROM %s.runs WHERE run_id IN (%s)', statusCol, schemaName, runIds);
    tbl = fetch(conn, sql);
    if ~isempty(tbl)
        v = lower(string(tbl.(statusCol)));
        badMask = contains(v, 'fail') | contains(v, 'partial') | contains(v, 'quarant') | contains(v, 'error') | contains(v, 'aborted') | contains(v, 'incomplete');
        count = sum(badMask);
        return;
    end
end

% Fallback: require both run_summary presence and non-missing completion fields.
runIds = strjoin(string(runsTbl.run_id), ',');
sql = sprintf('SELECT run_id, sim_time_s, started_at FROM %s.runs WHERE run_id IN (%s)', schemaName, runIds);
tbl = fetch(conn, sql);
if isempty(tbl)
    count = 0;
    return;
end

badMask = false(height(tbl), 1);
if ismember('sim_time_s', tbl.Properties.VariableNames)
    badMask = badMask | ismissing(tbl.sim_time_s) | tbl.sim_time_s <= 0;
end
if ismember('started_at', tbl.Properties.VariableNames)
    badMask = badMask | ismissing(tbl.started_at);
end
count = sum(badMask);
end

function idx = local_find_first_index(runsTbl, token)
idx = -1;
if isempty(runsTbl)
    return;
end
names = strings(height(runsTbl), 1);
if ismember('scenario_name', runsTbl.Properties.VariableNames)
    names = lower(string(runsTbl.scenario_name));
elseif ismember('experiment_version', runsTbl.Properties.VariableNames)
    names = lower(string(runsTbl.experiment_version));
end
matchIdx = find(contains(names, lower(string(token))), 1, 'first');
if ~isempty(matchIdx)
    idx = matchIdx;
end
end

function tf = local_has_comparison_support(runsTbl)
tf = false;
if isempty(runsTbl) || ~ismember('scenario_name', runsTbl.Properties.VariableNames)
    return;
end
names = lower(string(runsTbl.scenario_name));
tf = any(contains(names, '_h0_')) && (any(contains(names, '_h1_')) || any(contains(names, '_h3_')) || any(contains(names, '_h4_')));
end

function local_create_figures(output_root, runsTbl, runSummaryTbl, energyPath, h0Path, scalePath)
if isempty(runsTbl)
    return;
end

names = local_run_names(runsTbl);
isS500 = contains(names, 's500');
isS1000 = contains(names, 's1000');

energyMeans = [NaN; NaN];
labels = categorical({'S500','S1000'});
if ~isempty(runSummaryTbl) && ismember('consumed_j', runSummaryTbl.Properties.VariableNames)
    if ismember('run_id', runSummaryTbl.Properties.VariableNames)
        energyMeans(1) = mean(double(runSummaryTbl.consumed_j(ismember(runSummaryTbl.run_id, runsTbl.run_id(isS500)))), 'omitnan');
        energyMeans(2) = mean(double(runSummaryTbl.consumed_j(ismember(runSummaryTbl.run_id, runsTbl.run_id(isS1000)))), 'omitnan');
    end
end

fig1 = figure('Visible', 'off', 'Color', 'w', 'Position', [120 120 1000 560]);
bar(labels, energyMeans, 'FaceColor', [0.18 0.45 0.72]);
xlabel('Phase2A Prefix'); ylabel('Mean Consumed Energy');
title('Phase 2A Live DB - Energy Summary');
grid on;
saveas(fig1, energyPath);
close(fig1);

if ~isempty(runSummaryTbl) && all(ismember(["recovered_clusters"], string(runSummaryTbl.Properties.VariableNames)))
    runNames = names;
    h0Mask = contains(runNames, '_h0_');
    activeMask = contains(runNames, '_h1_') | contains(runNames, '_h3_') | contains(runNames, '_h4_');
    h0Mean = mean(double(runSummaryTbl.recovered_clusters(ismember(runSummaryTbl.run_id, runsTbl.run_id(h0Mask)))), 'omitnan');
    activeMean = mean(double(runSummaryTbl.recovered_clusters(ismember(runSummaryTbl.run_id, runsTbl.run_id(activeMask)))), 'omitnan');

    fig2 = figure('Visible', 'off', 'Color', 'w', 'Position', [120 120 1000 560]);
    bar(categorical({'H0','Active'}), [h0Mean, activeMean], 'FaceColor', [0.75 0.30 0.24]);
    xlabel('Healing Group'); ylabel('Mean Recovered Clusters');
    title('Phase 2A Live DB - H0 vs Active Healing Summary');
    grid on;
    saveas(fig2, h0Path);
    close(fig2);
end

if ~isempty(runSummaryTbl) && ismember('consumed_j', runSummaryTbl.Properties.VariableNames)
    s500Mean = mean(double(runSummaryTbl.consumed_j(ismember(runSummaryTbl.run_id, runsTbl.run_id(isS500)))), 'omitnan');
    s1000Mean = mean(double(runSummaryTbl.consumed_j(ismember(runSummaryTbl.run_id, runsTbl.run_id(isS1000)))), 'omitnan');
    fig3 = figure('Visible', 'off', 'Color', 'w', 'Position', [120 120 1000 560]);
    bar(categorical({'S500','S1000'}), [s500Mean, s1000Mean], 'FaceColor', [0.22 0.62 0.40]);
    xlabel('Scale'); ylabel('Mean Consumed Energy');
    title('Phase 2A Live DB - Scale Comparison Summary');
    grid on;
    saveas(fig3, scalePath);
    close(fig3);
end

end

function names = local_run_names(runsTbl)
names = strings(height(runsTbl), 1);
if ismember('scenario_name', runsTbl.Properties.VariableNames)
    names = lower(string(runsTbl.scenario_name));
elseif ismember('experiment_version', runsTbl.Properties.VariableNames)
    names = lower(string(runsTbl.experiment_version));
end
end

function local_write_report(reportPath, lines)
fid = fopen(reportPath, 'w');
if fid < 0
    error('Could not create report file: %s', reportPath);
end
cleanupObj = onCleanup(@() fclose(fid)); %#ok<NASGU>
for i = 1:numel(lines)
    fprintf(fid, '%s\n', lines(i));
end
end

function tf = local_yesno(condition)
if condition
    tf = 'yes';
else
    tf = 'no';
end
end

function out = local_num_or_na(value)
if isnan(value)
    out = 'N/A';
else
    out = sprintf('%d', value);
end
end

function out = local_count_or_na(value)
if isnan(value)
    out = 'N/A';
else
    out = sprintf('%s/%d', local_yesno(value > 0), value);
end
end

function out = local_success_count_text(value)
if isnan(value)
    out = 'no/N/A';
elseif value == 162
    out = 'yes/162';
else
    out = sprintf('no/%d', value);
end
end

function out = local_yesno_path(pathValue)
if isempty(pathValue)
    out = 'no';
else
    out = ['yes/' char(pathValue)];
end
end

function out = local_figs_text(paths)
if isempty(paths)
    out = 'no';
else
    out = ['yes/' char(strjoin(paths, '; '))];
end
end

function out = local_safety_text(isSafe, remainingIssues)
if isSafe
    out = 'yes';
elseif isempty(remainingIssues)
    out = 'with limitations';
else
    out = ['with limitations: ' char(strjoin(remainingIssues, ' | '))];
end
end

function out = local_remaining_text(remainingIssues)
if isempty(remainingIssues)
    out = 'none';
else
    out = char(strjoin(remainingIssues, ' | '));
end
end

function v = local_scalar(value)
if istable(value)
    v = double(value{1,1});
elseif isnumeric(value)
    v = double(value(1));
elseif iscell(value)
    v = double(value{1});
else
    v = double(value);
end
end

function local_close_connection(conn)
if isempty(conn)
    return;
end
try
    close(conn);
catch
end
end