"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const core = __importStar(require("@actions/core"));
const child_process_1 = require("child_process");
const rest_1 = require("@octokit/rest");
const config_1 = require("./config");
const TMP_DIR = 'tmp';
const WORK_REF = 'sync-files';
const copyFiles = (repo, token) => {
    core.info(`Repo: ${repo.full_name}, Ref: ${repo.ref}`);
    try {
        const repoDir = path_1.default.join(TMP_DIR, repo.full_name);
        if (fs_1.default.existsSync(repoDir)) {
            fs_1.default.rmSync(repoDir, { recursive: true });
        }
        (0, child_process_1.execSync)(`git clone https://x-access-token:${token}@github.com/${repo.full_name}.git ${repoDir} --depth 1`);
        repo.files?.forEach(file => {
            core.info(`Copying ${file.src} to ${file.dest}`);
            const src = path_1.default.join(repoDir, file.src);
            const dest = path_1.default.join(process.cwd(), file.dest);
            fs_1.default.cpSync(src, dest, { recursive: true });
        });
    }
    catch (error) {
        if (error instanceof Error) {
            core.setFailed(error.message);
        }
    }
};
const main = async () => {
    const config = await (0, config_1.loadConfig)();
    const octokit = new rest_1.Octokit({ auth: config.token });
    const [owner, repo] = process.env.GITHUB_REPOSITORY?.split('/') ?? [];
    const baseBranch = (0, child_process_1.execSync)('git rev-parse --abbrev-ref HEAD').toString().trim();
    if (!fs_1.default.existsSync(TMP_DIR)) {
        fs_1.default.mkdirSync(TMP_DIR);
    }
    try {
        (0, child_process_1.execSync)(`git fetch origin ${WORK_REF}`);
        (0, child_process_1.execSync)(`git checkout -b ${WORK_REF} origin/${WORK_REF}`);
    }
    catch (error) {
        if (error instanceof Error) {
            core.error(error.message);
        }
        (0, child_process_1.execSync)(`git checkout -b ${WORK_REF} ${baseBranch}`);
    }
    config.repos.forEach(async (r) => copyFiles(r, config.token));
    try {
        (0, child_process_1.execSync)(`git config --local user.name ${config.username}`);
        (0, child_process_1.execSync)(`git config --local user.email ${config.email}`);
        (0, child_process_1.execSync)('git add -N .');
        if ((0, child_process_1.execSync)('git diff --name-only').toString().trim() !== '') {
            core.info('Committing');
            (0, child_process_1.execSync)('git add .');
            (0, child_process_1.execSync)('git commit -m "Sync files"');
            (0, child_process_1.execSync)(`git push origin ${WORK_REF}`);
            const pulls = await octokit.pulls.list({
                owner: owner,
                repo: repo,
                state: 'open',
                head: `${owner}:${WORK_REF}`,
            });
            if (pulls.data.length === 0) {
                await octokit.pulls.create({
                    owner: owner,
                    repo: repo,
                    title: 'Sync files',
                    head: WORK_REF,
                    base: baseBranch,
                });
            }
        }
    }
    catch (error) {
        if (error instanceof Error) {
            core.setFailed(error.message);
        }
    }
};
main();
