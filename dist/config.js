"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadConfig = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const js_yaml_1 = require("js-yaml");
const loadConfig = () => {
    let config = {
        token: fetchActionInput('token'),
        username: fetchActionInput('username'),
        email: fetchActionInput('email'),
        reviewers: fetchActionInput('reviewers').split(','),
        teamReviewers: fetchActionInput('team_reviewers').split(','),
        workRef: fetchActionInput('work_ref', 'repo-file-sync'),
        repos: [],
        pr_search_range: fetchActionInput('pr_search_range'),
    };
    try {
        const yaml = loadConfigYaml();
        for (const key of Object.keys(yaml)) {
            const [full_name, ref] = key.split('@');
            const [owner, name] = full_name.split('/');
            let repo = {
                owner: owner,
                name: name,
                full_name: full_name,
                ref: ref,
                files: [],
            };
            yaml[key].forEach((file) => {
                var _a;
                (_a = repo.files) === null || _a === void 0 ? void 0 : _a.push({
                    src: file,
                    dest: file,
                });
            });
            config.repos.push(repo);
        }
    }
    catch (error) {
        if (error instanceof Error) {
            throw error;
        }
    }
    return config;
};
exports.loadConfig = loadConfig;
const fetchActionInput = (key, defaultValue = '') => {
    return process.env[`INPUT_${key.toUpperCase()}`] || defaultValue;
};
const loadConfigYaml = () => {
    const configName = "repo-file-sync";
    let configPath = path_1.default.join(process.cwd(), '.github', `${configName}.yml`);
    if (!fs_1.default.existsSync(configPath)) {
        configPath = path_1.default.join(process.cwd(), '.github', `${configName}.yaml`);
        if (!fs_1.default.existsSync(configPath)) {
            throw new Error(`Config file not found`);
        }
    }
    return (0, js_yaml_1.load)(fs_1.default.readFileSync(configPath, 'utf8'));
};
