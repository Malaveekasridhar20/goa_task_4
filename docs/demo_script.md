# Demo Script: Fraud Investigation Agent

**Target Duration**: 3–5 minutes

## Introduction (30 seconds)
"Welcome. We are demonstrating an autonomous Fraud Investigation Agent powered by TigerGraph. When a suspicious transaction occurs, the agent dynamically traverses the graph, evaluates evidence against strict corporate policy, calculates an evidence-weighted fraud score, generates a Next-Best-Action, and writes its findings back into TigerGraph's case memory."

---

## CASE 1: Clear Fraud (HHG-010) (2 minutes)
*Goal: Demonstrate high-confidence fraud detection, SAR generation, and live graph write-back.*

**1. The Alert (Transaction & Graph Investigation)**
- **Action**: Load case HHG-010.
- **Talking point**: "A transaction alerts the agent. The agent queries TigerGraph, retrieving the immediate `O_Card` and `O_DeviceProfile` connections."

**2. Evidence & Pattern Extraction**
- **Action**: Show the extracted evidence.
- **Talking point**: "The graph reveals a Card Not Present (CNP) pattern. The transaction was online, for an unusual amount, originating from an unseen device."

**3. Probability & Uncertainty Assessment**
- **Action**: Highlight the Evidence-Weighted Fraud Score.
- **Talking point**: "Our deterministic scoring engine weighs this evidence, yielding a `1.0` fraud probability with `LOW` uncertainty."

**4. Policy Engine (NBA & SAR)**
- **Action**: Show the Next Best Action and SAR status.
- **Talking point**: "The Policy Engine receives the `1.0` score. It triggers `BLOCK_CARD` and `CREATE_CASE`. Because the exposure exceeds the $1,000 threshold ($1,000.03), it dynamically files a Suspicious Activity Report (SAR)."

**5. Graph Write-back**
- **Action**: Highlight `graph_write_status: VERIFIED`.
- **Talking point**: "The agent writes its decision back to TigerGraph as an `O_ClosedCase`, giving future agents immediate graph memory of this fraud."

---

## CASE 2: Borderline / Low Confidence (HHG-001) (2 minutes)
*Goal: Demonstrate uncertainty handling and customer verification.*

**1. The Alert & Limited Evidence**
- **Action**: Load case HHG-001.
- **Talking point**: "Now let's look at a borderline transaction. The agent queries the graph but finds only partial CNP indicators."

**2. Uncertainty & Probability**
- **Action**: Highlight the `0.65` score and `HIGH` uncertainty.
- **Talking point**: "Because of missing independent historical support, the pattern is only 'PARTIAL'. The evidence-weighted score sits at `0.65`, resulting in `HIGH` uncertainty."

**3. Policy Engine (NBA & No SAR)**
- **Action**: Show the NBA.
- **Talking point**: "Instead of blindly blocking the card, the Policy Engine respects the uncertainty. It triggers a `VERIFY_WITH_CUSTOMER` (step-up authentication). No SAR is filed since this is not confirmed fraud."

**4. Final Verification**
- **Action**: Show the graph write status.
- **Talking point**: "Even as an 'uncertain' case, the investigation is successfully written back to the graph, completing the continuous learning loop."
