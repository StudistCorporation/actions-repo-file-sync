export type ConfigYaml = { [key: string]: string[] }

export interface Config {
  token: string
  username: string
  email: string
  reviewers: string[]
  teamReviewers: string[]
  workRef: string
  repos: Repository[]
  pr_search_range: string
}

export interface File {
  src: string
  dest: string
}

export interface Repository {
  owner: string
  name: string
  full_name: string
  ref?: string
  files?: File[]
}
