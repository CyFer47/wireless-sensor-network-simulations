function test_db_connection()
% Test local MATLAB connection to VMware PostgreSQL DB

clc;
fprintf('=== MATLAB DB CONNECTION TEST ===\n');

cfg = db_config();
conn = [];

try
    conn = get_db_connection(cfg);
    runs = get_available_runs(conn, cfg.schema);

    fprintf('\n=== AVAILABLE RUNS ===\n');
    disp(runs);

    fprintf('PASS: MATLAB DB connectivity test completed.\n');
catch ME
    fprintf('FAIL: %s\n', ME.message);
end

if ~isempty(conn)
    try
        close(conn);
    catch
    end
end
end
