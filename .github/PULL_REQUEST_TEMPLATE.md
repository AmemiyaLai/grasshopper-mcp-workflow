<!--
  PR Title 格式建議: <type>[(<scope>)]: <description>
  例如: feat(auth): add google oauth2 login flow
        fix(ui-viewer): dispose webgl context on map unmount
        infra(k8s): bump ingress-nginx to 1.11.2
-->

## 變更概述

<!-- 請簡要描述這個 PR 做了什麼, 以及為什麼需要這個變更 -->

## 關聯 Issue

<!-- 必須填寫關聯的 Issue, 例如: Resolves #123, Fixes #456 -->
Resolves #

## 變更分類

- [ ] `feat` 新增功能 (Feature)
- [ ] `fix` 缺陷修復 (Bug Fix)
- [ ] `refactor` 架構重構或技術債清理 (Refactor)
- [ ] `perf` 效能優化 (Performance)
- [ ] `infra` 基礎設施 / GitOps / CI 流程變更
- [ ] `docs` 文件更新 (Documentation)
- [ ] `chore` 例行維護 / 套件依賴升級

## 核心變更細節

<!-- 列出具體的改動點, 影響模組與架構調整 -->
1. 
2. 

## 測試與驗證

<!-- 說明如何驗證這個變更 (例如單元測試結果、手動驗收步驟、截圖等) -->
- **測試方式**:
- **驗證結果**:

## Infrastructure / GitOps 專用區塊 (非 IaC 變更可略過)

<details>
<summary>點擊展開 Terraform Plan / GitOps Diff 輸出</summary>

```diff
# 在此貼上 plan 或 diff 輸出
```
</details>

- **Rollback 復原方案**: 

## Checklist (DoD)

- [ ] PR Title 符合 Conventional Commits 格式 (`<type>[(<scope>)]: <desc>`)
- [ ] 已關聯驅動此 PR 的 GitHub Issue
- [ ] 已通過本地所有 CI 檢查 (Build / Lint / Type Check / Test)
- [ ] 已更新相關 API 文件, 規格書或 `.env.example` (如需要)
- [ ] 程式碼皆已附帶適當的單元/整合測試
