import fs from 'fs';
import path from 'path';
import { load } from 'js-yaml';

export const loadConfig = (): Config => {
  let config: Config = {
    token: fetchActionInput('token'),
    username: fetchActionInput('username'),
    email: fetchActionInput('email'),
    reviewers: fetchActionInput('reviewers').split(','),
    teamReviewers: fetchActionInput('team_reviewers').split(','),
    workRef: fetchActionInput('work_ref', 'repo-file-sync'),
    repos: []
  }

  try {
    const yaml = loadConfigYaml()

    for (const key of Object.keys(yaml)) {
      const [full_name, ref] = key.split('@')
      const [owner, name] = full_name.split('/')
      let repo: Repository = {
        owner: owner,
        name: name,
        full_name: full_name,
        ref: ref,
        files: [],
      }

      yaml[key].forEach(file => {
        repo.files?.push({
          src: file,
          dest: file,
        })
      })

      config.repos.push(repo)
    }
  } catch(error: unknown) {
    if (error instanceof Error) {
      throw error
    }
  }

  return config
}

const fetchActionInput = (key: string, defaultValue: string = ''): string => {
  return process.env[`INPUT_${key.toUpperCase()}`] || defaultValue
}

const loadConfigYaml= (): ConfigYaml => {
  const configName = "repo-file-sync"
  let configPath = path.join(process.cwd(), '.github', `${configName}.yml`)
  if (! fs.existsSync(configPath)) {
    configPath = path.join(process.cwd(), '.github', `${configName}.yaml`)
    if (! fs.existsSync(configPath)) {
      throw new Error(`Config file not found`)
    }
  }

  return load(fs.readFileSync(configPath, 'utf8')) as ConfigYaml
}
