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
