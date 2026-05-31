# Changelog

## [1.1.0](https://github.com/hellatan/claude-skills/compare/claude-skills-v1.0.0...claude-skills-v1.1.0) (2026-05-31)


### Features

* **claude-md-init:** new skill for adding CLAUDE.md to existing repos ([#12](https://github.com/hellatan/claude-skills/issues/12)) ([b2d949f](https://github.com/hellatan/claude-skills/commit/b2d949f8163588edee0b6c02655de581ee1ab65f))
* **gh-actions-init:** add develop→main auto-PR workflow template ([#25](https://github.com/hellatan/claude-skills/issues/25)) ([6ac9834](https://github.com/hellatan/claude-skills/commit/6ac983402850844edef949096f689c2ee9f491c3))
* **gh-actions-init:** new skill for adding GitHub Actions to existing repos ([#4](https://github.com/hellatan/claude-skills/issues/4)) ([9b2c2ee](https://github.com/hellatan/claude-skills/commit/9b2c2eefaa9f3c22f79ff27caf2612b954fbbb46))
* **gitflow-init:** new skill for setting up gitflow on existing repos ([#10](https://github.com/hellatan/claude-skills/issues/10)) ([917579d](https://github.com/hellatan/claude-skills/commit/917579d56b3fa10d70145b7d32d107bf36456f72))
* package repo as the 'ht-skills' Claude Code plugin ([#19](https://github.com/hellatan/claude-skills/issues/19)) ([32cc398](https://github.com/hellatan/claude-skills/commit/32cc398ecf2c5149edf6f41f48dfe26a38c16a32))
* **precommit-init:** new skill for adding pre-commit to existing repos ([#11](https://github.com/hellatan/claude-skills/issues/11)) ([8a82db0](https://github.com/hellatan/claude-skills/commit/8a82db0795754652cb5a6cf9882634176748a16c))
* **project-scaffold:** add opt-in database (Drizzle) and auth (Better Auth) steps ([#28](https://github.com/hellatan/claude-skills/issues/28)) ([9e790dd](https://github.com/hellatan/claude-skills/commit/9e790dddebb01fcb8f44745096e900bdb92ea315))
* **project-scaffold:** emoji-grouped Step 7 summary ([#1](https://github.com/hellatan/claude-skills/issues/1)) ([47abc39](https://github.com/hellatan/claude-skills/commit/47abc393c1208d097c19a60dfe73ec9066ff5ebd))
* **project-scaffold:** scaffold per-repo git-workflow rule into new projects ([#15](https://github.com/hellatan/claude-skills/issues/15)) ([fe63539](https://github.com/hellatan/claude-skills/commit/fe635392362f11b332ef8c9004cc05f320a58bf7))
* **project-scaffold:** styling choice (CSS Modules default), opt-in Render Blueprint, track .env.example ([#26](https://github.com/hellatan/claude-skills/issues/26)) ([81b290d](https://github.com/hellatan/claude-skills/commit/81b290d56a6d29c981c9fbc0ca1092a751815163))
* scaffold commit-hygiene, env-lazy, and worktree convention rules ([#27](https://github.com/hellatan/claude-skills/issues/27)) ([900dc9c](https://github.com/hellatan/claude-skills/commit/900dc9cc317ef510d686af120fb7e25e2a0b0c85))
* **testing-init:** new skill for adding tests to existing repos ([#3](https://github.com/hellatan/claude-skills/issues/3)) ([64e330b](https://github.com/hellatan/claude-skills/commit/64e330bb6940b7b103a384a47470e8c0c5a7574b))


### Bug Fixes

* bump claude-skills repo's own workflows to Node 24-supporting majors ([#20](https://github.com/hellatan/claude-skills/issues/20)) ([ce61eca](https://github.com/hellatan/claude-skills/commit/ce61eca156898cf391a182b1375e0cdab52b7276))
* bump GitHub Actions to Node 24-supporting majors ([#6](https://github.com/hellatan/claude-skills/issues/6)) ([c2fb246](https://github.com/hellatan/claude-skills/commit/c2fb246c222f84876954425e8e0d42fd4b4f6fe4))
* **gh-actions-init:** correct fullstack-monorepo release-please config so first release auto-tags ([#24](https://github.com/hellatan/claude-skills/issues/24)) ([e454e79](https://github.com/hellatan/claude-skills/commit/e454e7962f367eccb537e271ce79503e268db2a6))
* **gitflow-init:** derive branch-protection contexts from ci.yml ([#16](https://github.com/hellatan/claude-skills/issues/16)) ([01f0280](https://github.com/hellatan/claude-skills/commit/01f0280d1418d1bff9d8be576cb2123e2d255124))
* **project-scaffold:** apply pre-commit auto-fixers before initial commit ([#14](https://github.com/hellatan/claude-skills/issues/14)) ([92e5c9d](https://github.com/hellatan/claude-skills/commit/92e5c9d3e1fa680ee5863c505ad9e774ead5847c))
* **project-scaffold:** avoid release-please 1.0.0 bootstrap on first release ([#22](https://github.com/hellatan/claude-skills/issues/22)) ([a5bc3a8](https://github.com/hellatan/claude-skills/commit/a5bc3a82a9351899b66aa9385e769e67cf5d5451))
* **project-scaffold:** correct release-please config so first release auto-tags ([#23](https://github.com/hellatan/claude-skills/issues/23)) ([9a3ad4f](https://github.com/hellatan/claude-skills/commit/9a3ad4f00dd9dd84660e0cc5f859f52d2338b509))
* **project-scaffold:** enable GitHub Actions to create PRs on freshly scaffolded repos ([#21](https://github.com/hellatan/claude-skills/issues/21)) ([c5fa58f](https://github.com/hellatan/claude-skills/commit/c5fa58f7c11f7f7c02e5d43ee39919645f368f69))
* **project-scaffold:** ignore .claude/worktrees/ in scaffolded repos and this repo ([#29](https://github.com/hellatan/claude-skills/issues/29)) ([06e7ac7](https://github.com/hellatan/claude-skills/commit/06e7ac70817db7fafd1bb208d10b6591614941b2))
* **project-scaffold:** replace deprecated 'next lint' with 'eslint' ([#17](https://github.com/hellatan/claude-skills/issues/17)) ([27d190b](https://github.com/hellatan/claude-skills/commit/27d190ba5cfc453ca2d121520754dc53571d3a3a))

## 1.0.0 (2026-05-31)


### Features

* **claude-md-init:** new skill for adding CLAUDE.md to existing repos ([#12](https://github.com/hellatan/claude-skills/issues/12)) ([b2d949f](https://github.com/hellatan/claude-skills/commit/b2d949f8163588edee0b6c02655de581ee1ab65f))
* **gh-actions-init:** add develop→main auto-PR workflow template ([#25](https://github.com/hellatan/claude-skills/issues/25)) ([6ac9834](https://github.com/hellatan/claude-skills/commit/6ac983402850844edef949096f689c2ee9f491c3))
* **gh-actions-init:** new skill for adding GitHub Actions to existing repos ([#4](https://github.com/hellatan/claude-skills/issues/4)) ([9b2c2ee](https://github.com/hellatan/claude-skills/commit/9b2c2eefaa9f3c22f79ff27caf2612b954fbbb46))
* **gitflow-init:** new skill for setting up gitflow on existing repos ([#10](https://github.com/hellatan/claude-skills/issues/10)) ([917579d](https://github.com/hellatan/claude-skills/commit/917579d56b3fa10d70145b7d32d107bf36456f72))
* package repo as the 'ht-skills' Claude Code plugin ([#19](https://github.com/hellatan/claude-skills/issues/19)) ([32cc398](https://github.com/hellatan/claude-skills/commit/32cc398ecf2c5149edf6f41f48dfe26a38c16a32))
* **precommit-init:** new skill for adding pre-commit to existing repos ([#11](https://github.com/hellatan/claude-skills/issues/11)) ([8a82db0](https://github.com/hellatan/claude-skills/commit/8a82db0795754652cb5a6cf9882634176748a16c))
* **project-scaffold:** add opt-in database (Drizzle) and auth (Better Auth) steps ([#28](https://github.com/hellatan/claude-skills/issues/28)) ([9e790dd](https://github.com/hellatan/claude-skills/commit/9e790dddebb01fcb8f44745096e900bdb92ea315))
* **project-scaffold:** emoji-grouped Step 7 summary ([#1](https://github.com/hellatan/claude-skills/issues/1)) ([47abc39](https://github.com/hellatan/claude-skills/commit/47abc393c1208d097c19a60dfe73ec9066ff5ebd))
* **project-scaffold:** scaffold per-repo git-workflow rule into new projects ([#15](https://github.com/hellatan/claude-skills/issues/15)) ([fe63539](https://github.com/hellatan/claude-skills/commit/fe635392362f11b332ef8c9004cc05f320a58bf7))
* **project-scaffold:** styling choice (CSS Modules default), opt-in Render Blueprint, track .env.example ([#26](https://github.com/hellatan/claude-skills/issues/26)) ([81b290d](https://github.com/hellatan/claude-skills/commit/81b290d56a6d29c981c9fbc0ca1092a751815163))
* scaffold commit-hygiene, env-lazy, and worktree convention rules ([#27](https://github.com/hellatan/claude-skills/issues/27)) ([900dc9c](https://github.com/hellatan/claude-skills/commit/900dc9cc317ef510d686af120fb7e25e2a0b0c85))
* **testing-init:** new skill for adding tests to existing repos ([#3](https://github.com/hellatan/claude-skills/issues/3)) ([64e330b](https://github.com/hellatan/claude-skills/commit/64e330bb6940b7b103a384a47470e8c0c5a7574b))


### Bug Fixes

* bump claude-skills repo's own workflows to Node 24-supporting majors ([#20](https://github.com/hellatan/claude-skills/issues/20)) ([ce61eca](https://github.com/hellatan/claude-skills/commit/ce61eca156898cf391a182b1375e0cdab52b7276))
* bump GitHub Actions to Node 24-supporting majors ([#6](https://github.com/hellatan/claude-skills/issues/6)) ([c2fb246](https://github.com/hellatan/claude-skills/commit/c2fb246c222f84876954425e8e0d42fd4b4f6fe4))
* **gh-actions-init:** correct fullstack-monorepo release-please config so first release auto-tags ([#24](https://github.com/hellatan/claude-skills/issues/24)) ([e454e79](https://github.com/hellatan/claude-skills/commit/e454e7962f367eccb537e271ce79503e268db2a6))
* **gitflow-init:** derive branch-protection contexts from ci.yml ([#16](https://github.com/hellatan/claude-skills/issues/16)) ([01f0280](https://github.com/hellatan/claude-skills/commit/01f0280d1418d1bff9d8be576cb2123e2d255124))
* **project-scaffold:** apply pre-commit auto-fixers before initial commit ([#14](https://github.com/hellatan/claude-skills/issues/14)) ([92e5c9d](https://github.com/hellatan/claude-skills/commit/92e5c9d3e1fa680ee5863c505ad9e774ead5847c))
* **project-scaffold:** avoid release-please 1.0.0 bootstrap on first release ([#22](https://github.com/hellatan/claude-skills/issues/22)) ([a5bc3a8](https://github.com/hellatan/claude-skills/commit/a5bc3a82a9351899b66aa9385e769e67cf5d5451))
* **project-scaffold:** correct release-please config so first release auto-tags ([#23](https://github.com/hellatan/claude-skills/issues/23)) ([9a3ad4f](https://github.com/hellatan/claude-skills/commit/9a3ad4f00dd9dd84660e0cc5f859f52d2338b509))
* **project-scaffold:** enable GitHub Actions to create PRs on freshly scaffolded repos ([#21](https://github.com/hellatan/claude-skills/issues/21)) ([c5fa58f](https://github.com/hellatan/claude-skills/commit/c5fa58f7c11f7f7c02e5d43ee39919645f368f69))
* **project-scaffold:** ignore .claude/worktrees/ in scaffolded repos and this repo ([#29](https://github.com/hellatan/claude-skills/issues/29)) ([06e7ac7](https://github.com/hellatan/claude-skills/commit/06e7ac70817db7fafd1bb208d10b6591614941b2))
* **project-scaffold:** replace deprecated 'next lint' with 'eslint' ([#17](https://github.com/hellatan/claude-skills/issues/17)) ([27d190b](https://github.com/hellatan/claude-skills/commit/27d190ba5cfc453ca2d121520754dc53571d3a3a))
