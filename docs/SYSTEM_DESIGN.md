# System Design & Security Governance

VyapaarClaw implements a 6-layer protocol-level security enforcement model for managing AI financial expenditures. The pipeline leverages atomic database mutations and fails closed automatically to guarantee absolute control.

## Governance Execution Flow

```mermaid
flowchart TD
    %% Professional Flowchart Styling
    classDef default fill:#FFFFFF,stroke:#333333,stroke-width:2px,color:#333333,font-family:sans-serif;
    classDef trigger fill:#E0E7FF,stroke:#2563EB,color:#1E40AF,rx:8,ry:8,stroke-width:2px;
    classDef process fill:#F3F4F6,stroke:#4B5563,color:#1F2937,rx:8,ry:8,stroke-width:2px;
    classDef allow fill:#DCFCE7,stroke:#10B981,color:#065F46,rx:8,ry:8,stroke-width:2px;
    classDef reject fill:#FEE2E2,stroke:#EF4444,color:#991B1B,rx:8,ry:8,stroke-width:2px;
    classDef hold fill:#FEF3C7,stroke:#F59E0B,color:#92400E,rx:8,ry:8,stroke-width:2px;
    classDef boundary fill:none,stroke:#9CA3AF,stroke-width:2px,stroke-dasharray: 5 5;

    Start(["Agent Payout Request"]):::trigger --> CheckPol["1. Verify Agent Policy"]:::process
    
    CheckPol -- "Valid" --> CheckDom["2. Allowed Domain Validation"]:::process
    CheckPol -- "Invalid" --> R1["REJECT: NO_POLICY"]:::reject
    
    CheckDom -- "Valid" --> CheckTxn["3. Transaction Limit Check"]:::process
    CheckDom -- "Invalid" --> R2["REJECT: DOMAIN_BLOCKED"]:::reject
    
    CheckTxn -- "Under Limit" --> CheckML["4. ML Anomaly Scoring"]:::process
    CheckTxn -- "Exceeded" --> R3["REJECT: TXN_LIMIT_EXCEEDED"]:::reject
    
    CheckML -- "Low Risk" --> CheckRep["5. Reputation & Entity Verification"]:::process
    CheckML -- "High Risk" --> H1["HOLD: ML_FLAGGED"]:::hold
    
    CheckRep -- "Safe" --> CheckDaily["6. Daily Budget Constraint Check"]:::process
    CheckRep -- "Flagged" --> R4["REJECT: RISK_HIGH"]:::reject
    
    CheckDaily -- "Within Budget" --> CheckApproval["7. Auto-Approval Threshold Check"]:::process
    CheckDaily -- "Exceeded" --> R5["REJECT: LIMIT_EXCEEDED"]:::reject
    
    CheckApproval -- "Requires Approval" --> H2["HOLD: APPROVAL_REQUIRED"]:::hold
    CheckApproval -- "Auto-Approve" --> App1["APPROVE: POLICY_OK"]:::allow
    
    H1 --> ManualReview["Human Review Process (Slack)"]:::process
    H2 --> ManualReview
    
    ManualReview -- "Approved" --> App2["APPROVE: HUMAN_OVERRIDE"]:::allow
    ManualReview -- "Denied" --> R6["REJECT: HUMAN_REJECTED"]:::reject
```

### The Security Pipeline (Fail-Closed)

Our governance decision engine guarantees an impenetrable firewall between the LLM and Razorpay. When an agent signals intent to execute a payout, it MUST clear the following layered gauntlet:

1. **Policy Presence Check**: The agent making the call must have a valid configured spend policy provisioned in Postgres.
2. **Domain Policy Enforcement**: Blacklisted or unauthorized domain destinations are instantly rejected.
3. **Transaction Limit Checking**: Hard ceiling checks on individual atomic payload values.
4. **Machine Learning Anomaly Engine**: Spending pattern validation. Historical norms are analyzed off-grid using `IsolationForest` via scikit-learn. Unusual hours or velocity frequency vectors trigger a preemptive `HOLD` state.
5. **Vendor Reputation**:
    - **Google Safe Browsing v4**: Deep lookup of recipient vendor links to block phishing and malware proxies.
    - **GLEIF Entity Verification**: Ensuring the legal entity is registered globally.
6. **Atomic Redis Budget Limits Check**: Enforces immutable rate-limiting windows and precise daily budget deduction via `INCRBY` logic. If multiple agents attempt a race-condition payout, Redis operations sequentially enforce the ledger.

Finally, if the amount surpasses the pre-configured *auto-approval threshold* — or if the ML flagged a suspicious anomaly — the transaction goes into a strict manual `HOLD` state and escalates to a human operator via Slack callback ping for the final verdict.
