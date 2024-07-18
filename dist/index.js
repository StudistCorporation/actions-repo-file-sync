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
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
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
const TMP_DIR = "tmp";
const copyFiles = (repo, since, token) => {
    var _a;
    core.info(`Repo: ${repo.full_name}, Ref: ${repo.ref}`);
    try {
        const repoDir = path_1.default.join(TMP_DIR, repo.full_name);
        if (fs_1.default.existsSync(repoDir)) {
            fs_1.default.rmSync(repoDir, { recursive: true });
        }
        (0, child_process_1.execSync)(`git clone https://x-access-token:${token}@github.com/${repo.full_name}.git ${repoDir}`);
        const srcFiles = repo.files ? `-- ${repo.files.map((f) => f.src).join(" ")}` : ""; // ="file1 file2 file3"
        core.info(`Diff files are ${srcFiles}`);
        const mergedPulls = repo.files ? (0, child_process_1.execSync)(`git log origin  --oneline  --pretty=format:'%s' --since='${since}' ${srcFiles}  | grep -o '#[0-9]*'||true`, { cwd: repoDir })
            .toString()
            .split("\n") : []; // ["#123", "#456"]
        core.info(`Related PRs are ${mergedPulls}`);
        (_a = repo.files) === null || _a === void 0 ? void 0 : _a.forEach((file) => {
            core.info(`Copying ${file.src} to ${file.dest}.`);
            const src = path_1.default.join(repoDir, file.src);
            const dest = path_1.default.join(process.cwd(), file.dest);
            fs_1.default.cpSync(src, dest, { recursive: true });
        });
        return mergedPulls;
    }
    catch (error) {
        if (error instanceof Error) {
            core.setFailed(error.message);
        }
    }
};
const main = () => __awaiter(void 0, void 0, void 0, function* () {
    var _a, _b, _c;
    const config = yield (0, config_1.loadConfig)();
    const octokit = new rest_1.Octokit({ auth: config.token });
    const [owner, repo] = (_b = (_a = process.env.GITHUB_REPOSITORY) === null || _a === void 0 ? void 0 : _a.split("/")) !== null && _b !== void 0 ? _b : [];
    const baseBranch = (0, child_process_1.execSync)("git rev-parse --abbrev-ref HEAD")
        .toString()
        .trim();
    if (!fs_1.default.existsSync(TMP_DIR)) {
        fs_1.default.mkdirSync(TMP_DIR);
    }
    try {
        (0, child_process_1.execSync)(`git fetch origin ${config.workRef}`);
        (0, child_process_1.execSync)(`git checkout -b ${config.workRef} origin/${config.workRef}`);
    }
    catch (error) {
        if (error instanceof Error) {
            core.error(error.message);
        }
        (0, child_process_1.execSync)(`git checkout -b ${config.workRef} ${baseBranch}`);
    }
    const changeSummaries = config.repos.map((r) => { return { repo: r, pulls: copyFiles(r, config.pr_search_range, config.token) }; });
    try {
        (0, child_process_1.execSync)(`git config --local user.name ${config.username}`);
        (0, child_process_1.execSync)(`git config --local user.email ${config.email}`);
        (0, child_process_1.execSync)("git add -N .");
        if ((0, child_process_1.execSync)("git diff --name-only").toString().trim() !== "") {
            core.info("Committing");
            (0, child_process_1.execSync)("git add .");
            (0, child_process_1.execSync)('git commit -m "[repo-file-sync] Synchronize files"');
            (0, child_process_1.execSync)(`git push origin ${config.workRef}`);
            const pulls = yield octokit.pulls.list({
                owner: owner,
                repo: repo,
                state: "open",
                head: `${owner}:${config.workRef}`,
            });
            if (pulls.data.length === 0) {
                const summary = changeSummaries.find(f => f.repo.name == repo && f.repo.owner === owner);
                const prLinks = (_c = summary === null || summary === void 0 ? void 0 : summary.pulls) === null || _c === void 0 ? void 0 : _c.map(pr => `${summary.repo.full_name}${pr}`); // "owner/repo#123"[]
                const pull = yield octokit.pulls.create({
                    owner: owner,
                    repo: repo,
                    title: "[repo-file-sync] Synchronize files",
                    head: config.workRef,
                    base: baseBranch,
                    body: `
          # Related PRs
          ${prLinks === null || prLinks === void 0 ? void 0 : prLinks.map(l => `- ${l}`).join("\n")}
          `
                });
                if (config.reviewers.length !== 0 ||
                    config.teamReviewers.length !== 0) {
                    yield octokit.pulls.requestReviewers({
                        owner: owner,
                        repo: repo,
                        pull_number: pull.data.number,
                        reviewers: config.reviewers,
                        team_reviewers: config.teamReviewers,
                    });
                }
            }
        }
    }
    catch (error) {
        if (error instanceof Error) {
            core.setFailed(error.message);
        }
    }
});
main();
