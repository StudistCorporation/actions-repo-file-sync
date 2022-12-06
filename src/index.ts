import fs from 'fs';
import path from 'path';
import * as core from '@actions/core';
import { execSync } from 'child_process';
import { Octokit } from '@octokit/rest';

import { loadConfig } from '@/config';

const TMP_DIR = 'tmp'

const copyFiles = (repo: Repository, token: string) => {
  core.info(`Repo: ${repo.full_name}, Ref: ${repo.ref}`)

  try {
    const repoDir = path.join(TMP_DIR, repo.full_name)
    if (fs.existsSync(repoDir)) {
      fs.rmSync(repoDir, { recursive: true })
    }

    execSync(`git clone https://x-access-token:${token}@github.com/${repo.full_name}.git ${repoDir} --depth 1`)
    repo.files?.forEach(file => {
      core.info(`Copying ${file.src} to ${file.dest}`)
      const src = path.join(repoDir, file.src)
      const dest = path.join(process.cwd(), file.dest)
      fs.cpSync(src, dest, { recursive: true })
    })
  } catch (error: unknown) {
    if (error instanceof Error) {
      core.setFailed(error.message)
    }
  }
}

const main = async () => {
  const config = await loadConfig()
  const octokit = new Octokit({ auth: config.token })
  const [owner, repo] = process.env.GITHUB_REPOSITORY?.split('/') ?? []
  const baseBranch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim()

  if (! fs.existsSync(TMP_DIR)) {
    fs.mkdirSync(TMP_DIR)
  }

  try {
    execSync(`git fetch origin ${config.workRef}`)
    execSync(`git checkout -b ${config.workRef} origin/${config.workRef}`)
  } catch(error: unknown) {
    if (error instanceof Error) {
      core.error(error.message)
    }
    execSync(`git checkout -b ${config.workRef} ${baseBranch}`)
  }

  config.repos.forEach(async r => copyFiles(r, config.token))

  try {
    execSync(`git config --local user.name ${config.username}`)
    execSync(`git config --local user.email ${config.email}`)

    execSync('git add -N .')
    if (execSync('git diff --name-only').toString().trim() !== '') {
      core.info('Committing')
      execSync('git add .')
      execSync('git commit -m "[repo-file-sync] Synchronize files"')
      execSync(`git push origin ${config.workRef}`)

      const pulls = await octokit.pulls.list({
        owner: owner,
        repo: repo,
        state: 'open',
        head: `${owner}:${config.workRef}`,
      })
      if (pulls.data.length === 0) {
        const pull = await octokit.pulls.create({
          owner: owner,
          repo: repo,
          title: '[repo-file-sync] Synchronize files',
          head: config.workRef,
          base: baseBranch,
        })
        if (config.reviewers.length !== 0 || config.teamReviewers.length !== 0) {
          await octokit.pulls.requestReviewers({
            owner: owner,
            repo: repo,
            pull_number: pull.data.number,
            reviewers: config.reviewers,
            team_reviewers: config.teamReviewers,
          })
        }
      }
    }
  } catch (error: unknown) {
    if (error instanceof Error) {
      core.setFailed(error.message)
    }
  }
}

main()
