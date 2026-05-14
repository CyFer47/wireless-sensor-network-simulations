% MATLAB startup script for WSN Database project
% This runs automatically when MATLAB starts

% Add project paths
addpath(fullfile(pwd, 'config'));
addpath(fullfile(pwd, 'lib'));
addpath(fullfile(pwd, 'scripts'));

fprintf('=====================================================\n');
fprintf('WSN Database Project - Paths Configured\n');
fprintf('=====================================================\n');
fprintf('Current directory: %s\n', pwd);
fprintf('Paths added:\n');
fprintf('  - config\n');
fprintf('  - lib\n');
fprintf('  - scripts\n');
fprintf('\nTo test connection, run:\n');
fprintf('  test_db_connection\n');
fprintf('  test_single_run\n');
fprintf('=====================================================\n\n');
