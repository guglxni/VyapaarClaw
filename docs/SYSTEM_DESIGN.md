# System Design & Security Governance

VyapaarClaw implements a 6-layer protocol-level security enforcement model for managing AI financial expenditures. The pipeline leverages atomic database mutations and fails closed automatically to guarantee absolute control.

## Governance Execution Flow

```mermaid
graph TD
    %% Scientific Flowchart
    classDef io fill:#000,stroke:#000,color:#fff,font-family:monospace;
    classDef step fill:#fff,stroke:#000,stroke-width:1px,font-family:monospace;
    classDef cond fill:#fff,stroke:#000,stroke-width:1px,font-family:monospace;
    classDef terminal fill:#f0f0f0,stroke:#333,stroke-width:1px,stroke-dasharray: 4 4,font-family:monospace;

    Start(["Input: Agent Payout Request"]):::io --> CheckPol{"1. Policy<br/>Valid?"}:::cond
    CheckPol -- Yes --> CheckDom{"2. Domain<br/>Allowed?"}:::cond
    CheckPol -- No --> R1["Reject (NO_POLICY)"]:::terminal
    
    CheckDom -- Yes --> CheckTxn{"3. Under<br/>Txn Limit?"}:::cond
    CheckDom -- No --> R2["Reject (DOMAIN_BLOCKED)"]:::terminal
    
    CheckTxn -- Yes --> CheckML{"4. Anomaly<br/>Score OK?"}:::cond
    CheckTxn -- No --> R3["Reject (LIMIT_EXCEEDED)"]:::terminal
    
    CheckML -- Pass --> CheckRep{"5. Reputation<br/>Safe?"}:::cond
    CheckML -- Fail --> H1["Hold (ML_FLAGGED)"]:::step
    
    CheckRep -- Yes --> CheckBud{"6. Budget<br/>Available?"}:::cond
    CheckRep -- No --> R4["Reject (RISK_HIGH)"]:::terminal
    
    CheckBud -- Yes --> CheckAuto{"7. Auto<br/>Approve?"}:::cond
    CheckBud -- No --> R5["Reject (NO_FUNDS)"]:::terminal
    
    CheckAuto -- Yes --> App["Approve Payout"]:::terminal
    CheckAuto -- No --> H2["Hold (REQUIRE_L1)"]:::step
    
    H1 --> M["Manual Review via Slack"]:::step
    H2 --> M
    M -- Approve --> App
    M -- Deny --> R6["Reject (OVERRIDE)"]:::terminal
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
