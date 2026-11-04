# Assumptions

Choices not fixed by the task or the data documentation. Code that depends on one of these carries an `# ASSUMPTION:` comment.

## Data

- **Snapshot date.** The file has no explicit extract date. The latest `last_pymnt_d` is Mar 2019, so the snapshot is taken as 2019-03-31 (dbt var `snapshot_date`).
- **Borrower key.** `member_id` is empty in the public file, so a borrower cannot be followed across loans. Each loan has its own anonymous borrower profile keyed by the loan id.
- **Dropped columns.** Free text and identifiers that are not needed (url, desc, emp_title, title, member_id, zip_code) are dropped in staging.

## Label, censoring and maturity

Decided with the user on 2026-11-04.

- **Label.** Bad (1) = Charged Off or Default. Good (0) = Fully Paid. The "Does not meet the credit policy. Status: ..." variants map to the same values.
- **Censoring.** Current, In Grace Period and Late loans have no final outcome. They are excluded from training and evaluation (`is_bad` is null).
- **Maturity.** Only 36-month loans issued 2007 to 2015 are used. All 36-month vintages through 2014 are fully resolved and 2015 is 99.9% resolved (`results/m1_data_quality.json`, `by_vintage`), so dropping the unresolved loans does not bias the bad rate toward early defaults. For later vintages the resolved loans over-represent early defaults, so those vintages are not used. 60-month loans are excluded; their latest fully matured vintage is 2013, which would leave them out of the test years.
- **Out-of-time splits.** Train: issue years 2007 to 2012. Validation: 2013. Test: 2014 and 2015, reported separately.

## Features (M2)

- **Decision time** is the loan's issue month. Features come only from `core.loans` and `core.borrowers`. Every raw column is classified in `dbt/seeds/column_policy.csv`; only `application` columns may be used. `funded_amnt` and `funded_amnt_inv` are treated as post-origination, because they are set during funding.
- **Bureau attributes added by Lending Club around 2012** (about 30 columns such as `tot_cur_bal`, `bc_util`, `mort_acc`, `num_actv_bc_tl`) are empty for every loan issued 2007 to 2011 and for about half of 2012. They are not used, because they would be absent from training and present in test. Revisit in M6 (for example a model trained on 2013 onward).
- **Other columns not used:** `initial_list_status` (a listing mechanism introduced in 2012, not borrower risk), `application_type` and the joint-application fields (joint applications start in late 2015), `policy_code`, `disbursement_method`.
- **Sentinels.** `dti` values below 0 or at 999 are set to null.
- **Missing values** are left as null in SQL. `mths_since_last_delinq` and `mths_since_last_record` are null when there is no such event, so missingness carries information; each model handles it explicitly (M3).
- **Lending Club grade and interest rate are features.** They are Lending Club's own risk pricing, known at issue. A model that uses them partly reproduces Lending Club's model.
