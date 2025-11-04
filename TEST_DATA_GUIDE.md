# Test Data Guide for SecureGuard Fraud Detection System

## Form Field Reference

Based on your dataset structure and forms, here are realistic test scenarios you can use.

---

## Quick Scan Form (Basic)

### Required Fields:
1. **Time Sequence** (`step`)
2. **Transaction Amount** (`amount`)
3. **Customer Gender** (`gender`)
4. **Transaction Category** (`category`)

---

## Test Scenarios for Quick Scan

### ✅ Scenario 1: Legitimate Small Transaction
**Use Case**: Typical grocery purchase by female customer

- **Time Sequence**: `150`
- **Transaction Amount**: `45.50`
- **Customer Gender**: `Female (1)`
- **Transaction Category**: `🛒 Grocery/Food (0)`

**Expected Result**: Legitimate Transaction (Low Risk)

---

### ✅ Scenario 2: Legitimate Medium Transaction
**Use Case**: Gas station purchase by male customer

- **Time Sequence**: `320`
- **Transaction Amount**: `85.00`
- **Customer Gender**: `Male (0)`
- **Transaction Category**: `⛽ Gas Station (1)`

**Expected Result**: Legitimate Transaction (Low Risk)

---

### ⚠️ Scenario 3: Moderate Risk Transaction
**Use Case**: High-value online purchase

- **Time Sequence**: `450`
- **Transaction Amount**: `1,250.00`
- **Customer Gender**: `Male (0)`
- **Transaction Category**: `💻 Online Purchase (4)`

**Expected Result**: May trigger Medium Risk (monitoring recommended)

---

### 🚨 Scenario 4: High Risk Transaction
**Use Case**: Very large cash withdrawal at unusual time

- **Time Sequence**: `820`
- **Transaction Amount**: `8,500.00`
- **Customer Gender**: `Female (1)`
- **Transaction Category**: `🏧 ATM/Cash (8)`

**Expected Result**: High Risk or Potential Fraud Detection

---

### 🚨 Scenario 5: Suspicious Large Transaction
**Use Case**: Extremely high-value entertainment purchase

- **Time Sequence**: `950`
- **Transaction Amount**: `25,000.00`
- **Customer Gender**: `Male (0)`
- **Transaction Category**: `🎬 Entertainment (2)`

**Expected Result**: Very High Risk - Likely Fraud Detection

---

## Deep Analysis Form (Advanced)

### Required Fields:
1. **Time Sequence** (`step`)
2. **Customer ID** (`customer`)
3. **Age Category** (`age`)
4. **Gender Profile** (`gender`)
5. **Transaction Amount** (`amount`)
6. **Transaction Category** (`category`)
7. **Merchant ID** (`merchant_id`)

---

## Test Scenarios for Deep Analysis

### ✅ Scenario 1: Legitimate Regular Customer
**Use Case**: Middle-aged male regular customer buying groceries

- **Time Sequence**: `200`
- **Customer ID**: `12345`
- **Age Category**: `👔 Middle Age (36-50) - 2`
- **Gender Profile**: `Male (0)`
- **Transaction Amount**: `125.50`
- **Transaction Category**: `🛒 Grocery/Food (0)`
- **Merchant ID**: `5678`

**Expected Result**: Legitimate Transaction (Very Low to Low Risk)

---

### ✅ Scenario 2: Legitimate Healthcare Payment
**Use Case**: Senior female customer paying medical bills

- **Time Sequence**: `380`
- **Customer ID**: `23456`
- **Age Category**: `👴 Senior (65+) - 4`
- **Gender Profile**: `Female (1)`
- **Transaction Amount**: `450.00`
- **Transaction Category**: `🏥 Healthcare (6)`
- **Merchant ID**: `9012`

**Expected Result**: Legitimate Transaction (Low Risk)

---

### ⚠️ Scenario 3: Moderate Risk - Young Adult Large Purchase
**Use Case**: Young adult making expensive online purchase

- **Time Sequence**: `550`
- **Customer ID**: `34567`
- **Age Category**: `👶 Young Adult (18-25) - 0`
- **Gender Profile**: `Male (0)`
- **Transaction Amount**: `2,800.00`
- **Transaction Category**: `💻 Online Purchase (4)`
- **Merchant ID**: `3456`

**Expected Result**: Medium to High Risk (flagged for review)

---

### 🚨 Scenario 4: High Risk - Late Night Large Cash
**Use Case**: Adult customer withdrawing large amount late at night

- **Time Sequence**: `890`
- **Customer ID**: `45678`
- **Age Category**: `👨 Adult (26-35) - 1`
- **Gender Profile**: `Male (0)`
- **Transaction Amount**: `12,000.00`
- **Transaction Category**: `🏧 ATM/Cash (8)`
- **Merchant ID**: `7890`

**Expected Result**: High Risk - Fraud Alert Likely

---

### 🚨 Scenario 5: Suspicious Activity - Multiple Red Flags
**Use Case**: New customer, large travel expense, unusual time

- **Time Sequence**: `925`
- **Customer ID**: `1000`
- **Age Category**: `👶 Young Adult (18-25) - 0`
- **Gender Profile**: `Female (1)`
- **Transaction Amount**: `18,500.00`
- **Transaction Category**: `✈️ Travel (7)`
- **Merchant ID**: `1111`

**Expected Result**: Very High Risk - Fraud Detection

---

### 🚨 Scenario 6: Round Amount Suspicious Pattern
**Use Case**: Exact round amount transaction (money laundering indicator)

- **Time Sequence**: `750`
- **Customer ID**: `56789`
- **Age Category**: `👔 Middle Age (36-50) - 2`
- **Gender Profile**: `Male (0)`
- **Transaction Amount**: `15,000.00`
- **Transaction Category**: `🛍️ Shopping/Retail (3)`
- **Merchant ID**: `4567`

**Expected Result**: High Risk (round amount pattern detected)

---

## Field Value Reference

### Time Sequence (`step`)
- **Range**: 1 - 1000
- **Low values (1-300)**: Early in day/session
- **Medium values (301-600)**: Normal business hours
- **High values (601-1000)**: Late hours (higher fraud risk)

### Customer ID (`customer`)
- **Range**: 0 - 50,000
- **Lower IDs**: Potentially newer customers
- **Higher IDs**: Established customers

### Age Categories (`age`)
- **0**: 👶 Young Adult (18-25)
- **1**: 👨 Adult (26-35)
- **2**: 👔 Middle Age (36-50)
- **3**: 👨‍🦳 Mature (51-65)
- **4**: 👴 Senior (65+)

### Gender (`gender`)
- **0**: Male
- **1**: Female

### Transaction Categories (`category`)
- **0**: 🛒 Grocery/Food (Low risk)
- **1**: ⛽ Gas Station (Low risk)
- **2**: 🎬 Entertainment (Medium risk)
- **3**: 🛍️ Shopping/Retail (Low-Medium risk)
- **4**: 💻 Online Purchase (Medium-High risk)
- **5**: 🍽️ Restaurant (Low risk)
- **6**: 🏥 Healthcare (Low risk)
- **7**: ✈️ Travel (Medium-High risk)
- **8**: 🏧 ATM/Cash (High risk for large amounts)
- **9**: 🏠 Utilities (Low risk)
- **10**: 📦 Other (Medium risk)

### Transaction Amount (`amount`)
- **$0.01 - $100**: Small transactions (Low risk)
- **$100 - $500**: Normal transactions (Low risk)
- **$500 - $2,000**: Medium transactions (Low-Medium risk)
- **$2,000 - $10,000**: Large transactions (Medium-High risk)
- **$10,000+**: Very large transactions (High risk - requires review)

### Merchant ID (`merchant_id`)
- **Range**: 0 - 100,000
- **Any valid number works**
- **Consistency**: Same merchant ID for similar categories is realistic

---

## Risk Level Indicators

The system analyzes multiple factors to determine risk:

### 🟢 Low Risk (Legitimate)
- Normal amounts ($10-$500)
- Regular business hours (step 100-600)
- Common categories (grocery, gas, restaurant)
- Established customers

### 🟡 Medium Risk (Monitor)
- Higher amounts ($500-$5,000)
- Online or travel purchases
- Newer customers
- Late hours (step 600-800)

### 🟠 High Risk (Review Required)
- Large amounts ($5,000-$15,000)
- Very late hours (step 800+)
- Cash withdrawals
- Young customers with high amounts
- Round amounts ($5,000, $10,000, etc.)

### 🔴 Very High Risk (Fraud Alert)
- Extreme amounts ($15,000+)
- Multiple red flags combined
- Unusual patterns
- Very late transactions
- Inconsistent behavior

---

## Quick Testing Tips

1. **Start Simple**: Use Scenario 1 or 2 to verify legitimate detection
2. **Test Boundaries**: Try $2,000 and $10,000 amounts (threshold points)
3. **Time Matters**: High step values (800+) increase fraud probability
4. **Round Amounts**: Try $5,000, $10,000, $15,000 (flagged as suspicious)
5. **Category Risk**: ATM/Cash + Large Amount = High Risk
6. **Age Patterns**: Young adults + large amounts = Higher risk
7. **Watch Dashboard**: After each test, check the live dashboard updates

---

## Example Testing Flow

### Test 1: Verify System Works
Use Quick Scan Scenario 1 (Legitimate small transaction)
- Expect: ✅ Legitimate, Low Risk

### Test 2: Verify Fraud Detection
Use Quick Scan Scenario 5 (Suspicious large transaction)
- Expect: 🚨 Fraud Alert, Very High Risk

### Test 3: Check Dashboard Updates
- Submit 2-3 transactions
- Visit Dashboard (http://localhost:5000/)
- Verify statistics update
- Check "Recent Activity" feed

### Test 4: Test Deep Analysis
Use Deep Analysis Scenario 4 (High risk late night cash)
- Expect: 🚨 Fraud Alert with detailed risk factors

### Test 5: Verify API
After some transactions:
```bash
curl http://localhost:5000/api/stats
```

---

## Pro Tips

1. **Mix Transaction Types**: Test both legitimate and fraudulent to see the fraud rate percentage
2. **Watch Real-Time Updates**: Dashboard refreshes every 10 seconds
3. **Check Risk Distribution**: View how transactions are categorized by risk level
4. **Monitor Financial Metrics**: Total analyzed, fraud blocked, averages
5. **Review Recent Activity**: See last 10 transactions in real-time
6. **Test Edge Cases**: Try minimum ($0.01) and maximum ($999,999) amounts
7. **Time Patterns**: Test early (step 50), normal (step 400), and late (step 950)

---

## Common Patterns to Test

### Legitimate Patterns
- Small amounts + Common categories + Normal hours
- Healthcare/Utilities + Any amount + Any time
- Regular customers + Consistent behavior

### Fraud Patterns
- Large amounts + Cash/ATM + Late hours
- Round amounts + Travel/Entertainment
- Young customers + Very high amounts
- Online purchases + Extreme amounts
- Multiple red flags combined

---

## Troubleshooting

### If All Transactions Show Legitimate:
- Try higher amounts ($15,000+)
- Use late time steps (900+)
- Combine multiple risk factors
- Use ATM/Cash category with high amounts

### If All Transactions Show Fraud:
- Use lower amounts (<$500)
- Try early/normal time steps (100-400)
- Use low-risk categories (grocery, gas)
- Check model is loaded properly

### If Dashboard Not Updating:
- Refresh browser (F5)
- Wait 10 seconds for auto-refresh
- Check browser console for errors
- Verify API endpoint: http://localhost:5000/api/stats/live

---

**System Ready!** Start testing with these scenarios to see the full power of SecureGuard Fraud Detection System! 🛡️
