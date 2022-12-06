type ConfigYaml = { [key: string]: string[] }

interface Config {
  token: string
  username: string
  email: string
  reviewers: string[]
  teamReviewers: string[]
  workRef: string
  repos: Repository[]
}

interface File {
  src: string
  dest: string
}

interface Repository {
  owner: string
  name: string
  full_name: string
  ref?: string
  files?: File[]
}
