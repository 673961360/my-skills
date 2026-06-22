# AI Gateway API 接入手册

> 版本: v2.7 | 更新日期: 2026-06-18
>
> 本文档为 AI Gateway 全部 53 个接口的统一接入参考，包含 curl 测试串、请求参数、出参示例、字典值速查。
> 可直接用于接入方对接或作为 AI 学习材料。

---

## 第一章 快速开始

### 1.1 架构概述

AI Gateway 将后端微服务 API 和 Oracle SQL 查询统一注册为 HTTP 端点，外部系统通过 API Key 代理调用，无需直连数据库或知道内部微服务地址。

**调用链路**：

```
方式（测试环境直连）：
  调用方 → https://aitest.cjhxfund.com/ai-gateway → 后端微服务



### 1.2 认证方式

所有请求通过 HTTP Header 携带 API Key，格式：

```
Authorization: Bearer <API_KEY>
测试环境key为sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6
```

网关通过 API Key 自动注入以下参数，调用方**不需要**手动传递：
- `userId`（Header）— 自动注入
- `sysToken`（Header + JSON Body）— 自动注入

### 1.3 环境信息

| 环境 | Base URL                                 | API Key | 说明 |
|------|------------------------------------------|---------|------|
| **测试环境** | `https://aitest.cjhxfund.com/ai-gateway` | `sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6` | 直接调用 |
| **生产环境（via Nginx）** | `http://10.203.225.233:8089`             | 需联系管理员获取 | 办公网 Nginx 代理，仅开放查询接口，写操作返回 403 |
| **生产环境（直连）** | `https://生产地址打码`                         | 需联系管理员获取 | 完整权限 |

> **Nginx 代理说明**：生产环境通过 Nginx 代理时，17 个 API 只读查询 + 18 个 SQL 查询（共 35 个）可正常调用，12 个写操作接口被拦截返回 403。

### 1.4 接口总览


#### API 接口

| 接口ID | 名称 | 方法 | Body 类型 | 操作类型 | 风险等级 |
|--------|------|------|-----------|----------|----------|
| cat_api_trade_0008 | 查询实时正回购询价结果 | POST | json | 只读 | - |
| cat_api_trade_0021 | 进度汇总查询 | POST | json | 只读 | - |
| cat_api_trade_0022 | 头寸预测查询 | POST | form | 只读 | - |


#### SQL 查询接口

| 接口ID | 名称 | 数据源 | 参数 |
|--------|------|--------|------|
| cat_sql_trade_0001 | 查询交易日历 | ds_tdc | 无参数 |
| cat_sql_trade_0013 | 资金事件日历 | ds_tdc | beginDate, endDate |
| cat_sql_trade_0015 | 货币市场日期表 | ds_tdc | beginDate, endDate |
| cat_sql_trade_0019 | O32指令查询 | ds_tdc | queryDate |
| cat_sql_trade_0020 | 机器猫指令查询(不含组合指令) | ds_tdc | side_code_list, no_security_type |

### 1.5 curl 使用说明

根据接口类型，curl 命令有三种格式：

**模式一：JSON Body（POST）** — 适用于大部分 API 和全部 SQL 接口

```bash
curl -s -X POST "<BASE_URL>/admin/apiquery/proxy/<接口ID>" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

**模式二：Form Body（POST）** — 适用于 0001、0002、0007

```bash
curl -s -X POST "<BASE_URL>/admin/apiquery/proxy/<接口ID>" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "key1=value1&key2=value2"
```

**模式三：Query Params（GET）** — 适用于 0003、0016

```bash
curl -s -G "<BASE_URL>/admin/apiquery/proxy/<接口ID>" \
  -H "Authorization: Bearer <API_KEY>" \
  --data-urlencode "key1=value1" \
  --data-urlencode "key2=value2"
```

> 本文档中每个接口提供两个 curl 示例：`[测试环境]` 使用测试 Base URL + 明文 Key，`[生产环境·Nginx代理]` 使用 Nginx 地址 + 占位 Key。

### 1.6 Windows CMD 注意事项

本文档 curl 示例使用 bash 格式（`\` 换行），在 **Windows CMD** 中需做以下转换：

**1. 去掉换行符 `\`，合并为一行**

```cmd
REM bash 格式（文档中的写法）
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/dataquery/execute/cat_sql_trade_0001" ^
  -H "Authorization: Bearer sk-xxx" -H "Content-Type:/json" -d "{}"

REM CMD 格式（实际执行：去掉 \ 和换行，合并为一行）
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/dataquery/execute/cat_sql_trade_0001" -H "Authorization: Bearer sk-xxx" -H "Content-Type: application/json" -d "{}"
```

**2. JSON 中的单引号改双引号，内部双引号用 `\"` 转义**

```cmd
REM bash: 单引号包裹 JSON
-d '{"size":2000}'

REM CMD: 双引号包裹，内部双引号转义
-d "{\"size\":2000}"
```

**3. 示例对照**

以 `cat_api_trade_0003` 为例，文档中的 bash 格式：

```bash
curl -s -G "http://10.203.225.233:8089/admin/apiquery/proxy/cat_api_trade_0003" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  --data-urlencode "combiIdList=126,1275" \
  --data-urlencode "filterExpireBond=1"
```

CMD 直接可执行版本（复制即用）：

```cmd
curl -s -G "http://10.203.225.233:8089/admin/apiquery/proxy/cat_api_trade_0003" -H "Authorization: Bearer <PROD_API_KEY>" --data-urlencode "combiIdList=126,1275" --data-urlencode "filterExpireBond=1"
```

> **提示**：推荐使用 **Git Bash** 或 **PowerShell** 执行，可直接使用文档中的 bash 格式无需转换。

---

## 第二章 API 只读查询接口


### cat_api_trade_0021 — 进度汇总查询

进度汇总查询（分页查询交收明细）。

> **限速**：每分钟最多 2 次请求 ｜ **超时**：120 秒

**请求 URL**：`POST <BASE_URL>/admin/apiquery/proxy/cat_api_trade_0021`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/apiquery/proxy/cat_api_trade_0021" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/json" \
  -d '{"page":1,"size":100,"productIdList":[],"businDateStart":"20260601","businDateEnd":"20260601","businTypeList":[],"hideTgProductData":true,"hideInvalid":true,"showUnDeal":false,"hideSettleSuccess":false,"hideSettleByHandSuccess":false}'

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/apiquery/proxy/cat_api_trade_0021" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"page":1,"size":100,"productIdList":[],"businDateStart":"20260601","businDateEnd":"20260601","businTypeList":[],"hideTgProductData":true,"hideInvalid":true,"showUnDeal":false,"hideSettleSuccess":false,"hideSettleByHandSuccess":false}'
```

**请求参数**：

| Key | 类型 | 必填 | 说明 |
|-----|------|------|------|
| page | int | 是 | 页码 |
| size | int | 是 | 每页条数 |
| productIdList | array | 否 | 产品ID列表，为空表示全部 |
| businDateStart | string | 否 | 业务开始日期，格式 YYYYMMDD |
| businDateEnd | string | 否 | 业务结束日期，格式 YYYYMMDD |
| businTypeList | array | 否 | 业务类型列表，如 [1,5] 表示申赎 |
| hideTgProductData | bool | 否 | 是否隐藏T+G产品数据 |
| hideInvalid | bool | 否 | 是否隐藏无效数据 |
| showUnDeal | bool | 否 | 是否显示未成交数据 |
| hideSettleSuccess | bool | 否 | 是否隐藏交收成功数据 |
| hideSettleByHandSuccess | bool | 否 | 是否隐藏手工交收成功数据 |

**出参示例**：

```json
{
  "code": 0,
  "time": 1780301002625,
  "message": "success",
  "body": {
    "total": 941,
    "size": 100,
    "totalPage": 10,
    "page": 1,
    "rows": [
      {"capitalManager":"宋璟","settleState":"7","settleProgress":"1","settleOrder":null,"positionState":"7","productName":"创金合信聚利债券（工行）","estimatTransferCompleteTime":null,"businDate":"20260601","settleProgressMemo":null,"transferInstructCorrectness":"2","productTagUserName":"宋璟","crossMarketSign":"3","rivalId":"60638","o32InstructStateDesc":"成交已推","sqsBalance":0,"o32SecuritySettleState":"2","transferInstructState2":"2","productId":"1001","tradeNo":"CR20260601304085","rivalRiskLevel":"10120","zzdTotalBalance":0,"productTagTime":"20260601 15:11:48","o32InstructState":"3","cashSufficiency":null,"proSettleRiskLevel":"0","rowBackgroundColor":"1","dealTime":"2026-06-01 13:40:18","rivalRiskLevelDesc":"非公募基金非社保","estimatedCheckedTime":"13:50:18","tradeTypeDesc":"正回购","lendingDirectionDesc":"借","transferInstructStateDesc":"无需出具","dataTags":"","requirementTypeWithCurrentNodeExport":"","lastInitiateTime":null,"backstageEndTime":null,"o32SecuritySettleStateOperateSource":"1","topTag":null,"relativeNo":null,"settleState2Desc":"等调款，不跨市场","accountMaintenanceDesc":"已维护","rivalPayTime":"0","insId":41099899,"emergencyAdvice":null,"tgTransferEfficiency":10,"unitId":"31","requireForTransferTime":null,"traderivalName":"中信证券星云52号","fundSourceFeedback":null,"tradeType":"1","instructIssuingEfficiencyDesc":"","topTagDesc":"","combiId":"29","securityCode":"R001","lastCheckedTime":null,"pmOnDutyTime":"13:30至17:30","updateTime":"20260601 16:01:43","productDataTagDesc":"全部已完成(宋璟)","requirementTypeWithCurrentNode":null,"transferInstructState":"9","productCode":"001199","emergencyAdviceDesc":"","tghName":"工商银行","createTime":"20260601 13:16:53","o32InstructCorrectnessDesc":"指令错误","o32CapitalSettleStateDesc":"已交收","lendingDirection":"1","channelName":null,"combiName":"聚利固收","canIssueInstructionTime":null,"tradeEffectiveTime":null,"showAttachmentSendStateIcon":"0","atsTransferInstructStateDesc":"无需出具","inqResId":6219163,"o32CapitalSettleStateOperateSource":"1","settleAmt":18000000.0,"payableSettleRisk":"0","needPrintColumns":["transferInstructCorrectnessDesc"],"zzdBalance":0,"dataTagsDesc":"","tghBalance":2787709.11,"backDealTime":"2026-06-01 13:45:01","oldProductDataTag":null,"businType":"1","sqsTotalBalance":0,"o32CapitalSettleStateOperateDesc":"自动交收 系统 20260601 13:45:30","settleProgressDesc":"成功","o32CapitalSettleState":"2","frontDealStatus":"1","productTrader":"宋璟","advanceLevelDesc":null,"attachmentSendState":"0","accountMaintenance":"4","marketCodeDesc":"中债","pressForMoneySign":null,"o32SecuritySettleStateDesc":"已交收","toBeSettledSerialNo":"628484948","unitName":"聚利固收","productDataTag":"3","crossMarketSignDesc":"不跨市场","serialNo":"6945091","businTypeDesc":"银行间","settleState2":"7","tgbankTransferEfficiencyDesc":"","rivalPayTimeDesc":"","positionStateDesc":"交收头寸已平","lastTransferTime":null,"tgbankTransferEfficiency":null,"securityName":"R001","instructIssuingEfficiency":null,"singleSettleRisk":"0","requirementTypeWithCurrentNodeDesc":[],"transferInstructCorrectnessDesc":"指令错误","attachmentSendStateDesc":"无需发送","o32SecuritySettleStateOperateDesc":"自动交收 系统 20260601 13:45:30","orderNum":null,"onDutyTime":"08:30至11:30","bondInputer":null,"atsTransferInstructState":"9","receivableSettleRisk":"0","settleStateDesc":"等调款，不跨市场","ccTransferInstructState":"0","pressForMoneyStartTime":null,"pressForMoneyUser":null,"pressForMoneyTime":"","advanceLevel":null,"o32InstructionNo":874,"checkedTimeEfficiency":10,"pressForMoneySignDesc":null,"payableReceivableLevel":null,"marketCode":"1","pressForMoneyNum":"0","lastUrgingPaymentTime":null,"tradeDate":"20260601","frontDealTime":"2026-06-01 13:40:18","dataTagsUser":null,"zqName":"","fundSourceFeedbackDesc":"","dataTagsTime":"","cashSufficiencyDesc":null,"sameRivalDesc":"","startUrgingPaymentTime":null,"oldProductTagUserName":null,"payableReceivableLevelDesc":"","o32InstructCorrectness":"1"},
  ... // rows 数据已截断，仅展示部分字段
    ]
  }
}

### cat_api_trade_0022 — 头寸预测查询

头寸预测数据分页查询。请求体为 form 格式。

> **限速**：每分钟最多 3 次请求 ｜ **超时**：30 秒

**请求 URL**：`POST <BASE_URL>/admin/apiquery/proxy/cat_api_trade_0022`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/apiquery/proxy/cat_api_trade_0022" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "fundList=3M2099%2C3M2097&page=1&size=50&endDate=20260508&containTreatConfirmApply=0&containConfirmedRedeemFundBal=0&productLevel=0&managerLevel=0&positionStatus=&positionFlatDays=-1"

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/apiquery/proxy/cat_api_trade_0022" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "fundList=3M2099%2C3M2097&page=1&size=50&endDate=20260508&containTreatConfirmApply=0&containConfirmedRedeemFundBal=0&productLevel=0&managerLevel=0&positionStatus=&positionFlatDays=-1"
```

**请求参数**：

| Key | 类型 | 必填 | 说明 |
|-----|------|------|------|
| fundList | string | 否 | 产品代码列表，逗号分隔（URL编码） |
| page | int | 是 | 页码 |
| size | int | 是 | 每页条数 |
| endDate | string | 是 | 结束日期，格式 YYYYMMDD |
| containTreatConfirmApply | int | 否 | 包含待确认申赎申请，0=不包含 |
| containConfirmedRedeemFundBal | int | 否 | 包含已确认赎回基金余额，0=不包含 |
| productLevel | int | 否 | 产品层级，0=总头寸 |
| managerLevel | int | 否 | 管理人层级，0=默认 |
| positionStatus | string | 否 | 头寸状态，空=全部 |
| positionFlatDays | int | 否 | 头寸持平天数，-1=不限 |

**出参示例**：

```json
{
  "code": 0,
  "time": 1778122776051,
  "message": "success",
  "body": {
    "total": 30,
    "rows": [
      {
        "t0CashEnableBalInvest": 4569588.18,
        "stockSaleBalHgt": 0.0,
        "rqhgExpireBal": 0.0,
        "distributeBuyBal": 0.0,
        "settleReserveBal": 0.0,
        "zyzz": 0.0,
        "extractBal": 0.0,
        "bondDxDfBalCsi": 0.0,
        "futuresMarginBal": 0.0,
        "stockBuyBalHgt": 0.0,
        "rqhgExpireBalCibm": 0.0,
        "netStlBalCibmSqs": 0.0,
        "treatConfirmRedeemTaBalValue": 0.0,
        "riskSettleMarginAbs": 1950000.0,
        "fundCode": "3M2097",
        "netStlBal": 0.0,
        "yzzz": 0.0,
        "stockBuyBal": 0.0,
        "fundTransfer": 0.0,
        "rqhgBalCibm": 0.0,
        "confirmedRedeemFundBalValue": 0.0,
        "applyFundBal": 0.0,
        "redeemTaBal": 0.0,
        "netStlGuarBal": 0.0,
        "applyTaBal": 0.0,
        "rqhgExpireBalPact": 0.0,
        "rzhgBalCibm": 0.0,
        "bondDxDfBal": 0.0,
        "bondSaleBalCibm": 0.0,
        "manualAdjustBal": 0.0,
        "bondSaleBalNonGuar": 0.0,
        "stockBuyBalSgt": 0.0,
        "rzhgExpireBal": 0.0,
        "treatConfirmApplyTaBal": 0.0,
        "rzhgExpireBalCibm": 0.0,
        "dividendTaBal": 0.0,
        "positionStatusName": null,
        "redeemFundBal": 0.0,
        "fundName": "创金合信鼎泰46号（中行）",
        "bondSaleBalGuar": 0.0,
        "rzhgExpireBalPact": 0.0,
        "rzhgBalPact": 0.0,
        "bondBuyBalNonGuar": 0.0,
        "netStlNonGuarBal": 0.0,
        "netStlBalCibmZzd": 0.0,
        "treatConfirmApplyTaBalValue": 0.0,
        "appendExtractBal": 0.0,
        "treatConfirmRedeemTaBal": 0.0,
        "settleDate": 20260507,
        "vatBal": 0.0,
        "depositBal": 0.0,
        "rqhgBalPact": 0.0,
        "depositExpireBal": 0.0,
        "riskBalSgt": 0.0,
        "appendBal": 0.0,
        "stockSaleBalSgt": 0.0,
        "assetId": 1084,
        "t1CashEnableBalTrade": 4569588.18,
        "rzhgBal": 0.0,
        "bondDxDfBalCibm": 0.0,
        "t1CashEnableBalInvest": 4569588.18,
        "bondBuyBalCibm": 0.0,
        "riskBalHgt": 0.0,
        "netInflowBal": 0.0,
        "rqhgBal": 0.0,
        "otherBal": 0.0,
        "fundId": 2181,
        "bondBuyBalGuar": 0.0,
        "riskSettleMargin": 1950000.0,
        "positionStatus": 1,
        "stockSaleBal": 0.0,
        "netStlBalCibm": 0.0,
        "confirmedRedeemFundBal": 0.0,
        "assetName": "固收资产单元",
        "beginCash": 4569588.18
      },
      {
        "t0CashEnableBalInvest": 4569588.18,
        "stockSaleBalHgt": 0.0,
        "rqhgExpireBal": 0.0,
        "distributeBuyBal": 0.0,
        "settleReserveBal": 0.0,
        "zyzz": 0.0,
        "extractBal": 0.0,
        "bondDxDfBalCsi": 0.0,
        "futuresMarginBal": 0.0,
        "stockBuyBalHgt": 0.0,
        "rqhgExpireBalCibm": 0.0,
        "netStlBalCibmSqs": 0.0,
        "treatConfirmRedeemTaBalValue": 0.0,
        "riskSettleMarginAbs": 1950000.0,
        "fundCode": "3M2097",
```

---

```

---

### cat_api_trade_0023 — 询价结果明细查询

查询询价结果的明细信息，包含质押券列表。

> **限速**：每分钟最多 30 次请求 ｜ **超时**：30 秒

**请求 URL**：`POST <BASE_URL>/admin/apiquery/proxy/cat_api_trade_0023`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/apiquery/proxy/cat_api_trade_0023" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/json" \
  -d '{"inqResId":"2967","opDate":"20260507"}'

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/apiquery/proxy/cat_api_trade_0023" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"inqResId":"2967","opDate":"20260507"}'
```

**请求参数**：

| Key | 类型 | 必填 | 说明                                              |
|-----|------|------|-------------------------------------------------|
| inqResId | string | 是 | 询价结果ID,来自cat_api_trade_0008询价结果有返回该字段           |
| opDate | string | 是 | 操作日期，格式 YYYYMMDD,来自cat_api_trade_0008询价结果有返回该字段 |

**出参示例**：

```json
{
  "isBankRival": "1",
  "inqResId": "2967",
  "productId": "1023",
  "productCode": "003749",
  "productName": "创金合信鑫收益(招行)",
  "combiId": "467",
  "combiName": "股票组合",
  "bizType": "2",
  "bizTypeText": "银行间质押式回购",
  "sideCode": "7",
  "sideCodeText": "正回购",
  "repurAmt": "20000",
  "repurDay": "1",
  "repurRate": "0",
  "repoPriceType": "1",
  "repoPriceTypeText": "R加权",
  "clearSpeed": "1",
  "clearSpeedText": "T+0",
  "securityId": "1490016730",
  "securityCode": "R001",
  "securityName": "R001",
  "firstSettleDate": "20260507",
  "endSettleDate": "20260508",
  "firstSettleAmt": "20000",
  "endSettleAmt": "400883.97",
  "inqResStatus": "9",
  "inqResStatusText": "已下达",
  "mktId": "30",
  "mktName": "银行间",
  "rivalId": "13311",
  "rivalCode": "408067",
  "rivalName": "上清所",
  "rivalFullname": "银行间市场清算所股份有限公司",
  "interbankQuoteType": "1",
  "interbankQuoteTypeText": "对话报价",
  "processParallelStageText": "流程创建",
  "extRiskResultText": "无需处理",
  "pledgeSecurityList": [
    {
      "securityId": "1003115630",
      "securityCode": "1780264",
      "securityName": "17当涂经开债",
      "investType": "15",
      "investTypeText": "FVTPL",
      "mortgageRate": "0.2",
      "mortgageQty": "1000",
      "currentQty": "5000000",
      "trusteeText": "中债登托管",
      "outerCreditText": "AAA",
      "issuerCreditText": "AA-",
      "fullPrice": "62.8547",
      "mortgageAmt": "20000"
    }
  ]
}
```

---

### cat_sql_trade_0001 — 查询交易日历

查询交易日历，返回前 30 天到后 90 天的交易日。无参数。

> **限速**：每分钟最多 60 次请求 ｜ **超时**：30 秒

**请求 URL**：`POST <BASE_URL>/admin/dataquery/execute/cat_sql_trade_0001`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/dataquery/execute/cat_sql_trade_0001" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/json" \
  -d '{}'

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/dataquery/execute/cat_sql_trade_0001" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**请求参数**：无参数，直接发送空 JSON `{}`

**出参示例**：

```json
{
  "code": 0,
  "message": "success",
  "body": [
    {
      "TRADEDAY_TYPE_ID": 1,
      "SYS_DATE": 20260314,
      "WEEK_DAY": 6,
      "TRADEDAY_FLAG": 0,
      "SETTLEDAY_FLAG": 0,
      "OFFSET_DAY": 0,
      "VACATION_WORKING_FLAG": 0,
      "HK_SPECIAL_TRADEDAY_FLAG": 0
    },
    {
      "TRADEDAY_TYPE_ID": 3,
      "SYS_DATE": 20260314,
      "WEEK_DAY": 6,
      "TRADEDAY_FLAG": 0,
      "SETTLEDAY_FLAG": 0,
      "OFFSET_DAY": 0,
      "VACATION_WORKING_FLAG": 0,
      "HK_SPECIAL_TRADEDAY_FLAG": 0
    }
  ]
}


### cat_sql_trade_0013 — 资金事件日历

查询宏观资金操作日历。

> **限速**：每分钟最多 60 次请求 ｜ **超时**：60 秒

**请求 URL**：`POST <BASE_URL>/admin/dataquery/execute/cat_sql_trade_0013`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/dataquery/execute/cat_sql_trade_0013" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":20260101,"endDate":20260331}'

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/dataquery/execute/cat_sql_trade_0013" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":20260101,"endDate":20260331}'
```

**请求参数**：

| Key | 类型 | 必填 | 说明 |
|-----|------|------|------|
| beginDate | int | 是 | 开始日期，格式 YYYYMMDD（整数） |
| endDate | int | 是 | 结束日期，格式 YYYYMMDD（整数） |

**出参示例**：

```json
{
  "code": 0,
  "message": "success",
  "body": [
    {
      "STAT_DT": "2026-01-03T16:00:00.000+0000",
      "DATA_TYP": "明细",
      "EVNT_TYP_NM": "公开市场操作",
      "DIM1_NM": "逆回购",
      "DIM2_NM": "7D",
      "DIM3_NM": "投放",
      "INDX_VAL": 365,
      "DELFLAG": "0"
    },
    {
      "STAT_DT": "2026-01-03T16:00:00.000+0000",
      "DATA_TYP": "明细",
      "EVNT_TYP_NM": "公开市场操作",
      "DIM1_NM": "逆回购",
      "DIM2_NM": "7D",
      "DIM3_NM": "到期",
      "INDX_VAL": 2701,
      "DELFLAG": "0"
    }
  ]
}
```

### cat_sql_trade_0015 — 货币市场日期表

查询货币市场日期表。

> **限速**：每分钟最多 60 次请求 ｜ **超时**：60 秒

**请求 URL**：`POST <BASE_URL>/admin/dataquery/execute/cat_sql_trade_0015`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/dataquery/execute/cat_sql_trade_0015" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":20260101,"endDate":20261231}'

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/dataquery/execute/cat_sql_trade_0015" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":20260101,"endDate":20261231}'
```

**请求参数**：

| Key | 类型 | 必填 | 说明 |
|-----|------|------|------|
| beginDate | int | 是 | 开始日期，格式 YYYYMMDD（整数） |
| endDate | int | 是 | 结束日期，格式 YYYYMMDD（整数） |

**出参示例**：

```json
{
  "code": 0,
  "message": "success",
  "body": [
    {
      "STAT_DT": "2026-01-04T16:00:00.000+0000",
      "MONY_MKT_DT_TYP": "缴准日",
      "DELFLAG": "0"
    },
    {
      "STAT_DT": "2026-01-14T16:00:00.000+0000",
      "MONY_MKT_DT_TYP": "缴准日",
      "DELFLAG": "0"
    }
  ]
}

### cat_sql_trade_0019 — O32指令查询

按业务日期查询 O32 投资交易系统的指令数据，返回指令基本信息、证券明细、状态字典翻译等关键字段，覆盖现券买卖、质押/买断回购、场外基金等业务类型（单币种 CNY）。

> **限速**：每分钟最多 60 次请求 ｜ **超时**：120 秒

**请求 URL**：`POST <BASE_URL>/admin/dataquery/execute/cat_sql_trade_0019`

**curl 示例**：

```bash
# [测试环境]
curl -s -X POST "https://aitest.cjhxfund.com/ai-gateway/admin/dataquery/execute/cat_sql_trade_0019" \
  -H "Authorization: Bearer sk-7dPmKqHuGcrWnmvQB5sEQEBi0fFcPnc6" \
  -H "Content-Type: application/json" \
  -d '{"queryDate":20260611}'

# [生产环境·Nginx代理]
curl -s -X POST "http://10.203.225.233:8089/admin/dataquery/execute/cat_sql_trade_0019" \
  -H "Authorization: Bearer <PROD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"queryDate":20260611}'
```

**请求参数**：

| Key | 类型 | 必填 | 说明 |
|-----|------|------|------|
| queryDate | int | 是 | 业务日期，格式 YYYYMMDD，如 `20260611` |

**出参字段说明**：

返回 `body` 为数组，每条记录对应一条指令（按指令编号+修改序号聚合，多证券指令聚合为一行）。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 指令日期 | int | 业务日期 YYYYMMDD |
| 指令编号 | int | 当日指令流水号 |
| 修改序号 | int | 指令修改次数（初始=1） |
| 产品ID | int | 产品内部ID |
| 产品代码 | string | 产品代码（如 `001909`） |
| 产品名称 | string | 产品全称 |
| 组合ID | int | 组合内部ID |
| 组合名称 | string | 组合名称 |
| 指令类型 | string | 字典翻译：个股/组合/个股批量/组合批量 |
| 委托方向代码 | string | 原始方向码（如 `3`=债券买入, `5`=融资回购）；多方向时为 `"混合"` |
| 委托方向 | string | 方向中文名（如 `债券买入`, `融资回购`）；多方向时为 `"混合"` |
| 价格模式码 | string | 原始码值；多值时为空格 |
| 价格模式 | string | 字典翻译：如 `限价指令`、`不限价` |
| 指令价格(回购为利率) | number | 单价取 MIN，多券时为 `-1`；回购业务下即回购利率（%） |
| 指令状态码 | string | 原始码值 |
| 指令状态 | string | 字典翻译：如 `有效指令`、`已完成` |
| 委托状态码 | string | 聚合后：`1`=未执行, `2`=部分执行, `3`=已完成 |
| 委托状态 | string | 字典翻译：如 `未执行`、`部分执行`、`已完成` |
| 成交状态码 | string | 聚合后：`1`=未成交, `2`=部分成交, `3`=全部成交, `4`=成交失败 |
| 成交状态 | string | 字典翻译：如 `未成交`、`部分成交`、`全部成交` |
| 指令起始日期 | int | YYYYMMDD |
| 指令终止日期 | int | YYYYMMDD |
| 指令下达日期 | int | YYYYMMDD |
| 指令下达时间 | int | HHMMSS（如 `103116` 表示 10:31:16） |
| 指令金额 | number | SUM 聚合，单位元 |
| 成交金额 | number | SUM(en_total_deal_balance + en_today_deal_balance) |
| 指令数量 | number | SUM 聚合 |
| 证券内码 | string | O32 内部编码；多券时为 `"混合"` |
| 证券代码 | string | 对外交易代码（如 `250215`）；多券时为 `"混合"` |
| 证券名称 | string | 证券简称；多券时为 `"混合"` |
| 市场 | string | 市场名称（如 `银行间`）；多市场时为 `"混合"` |
| 业务分类 | string | 按市场归类：`银行间业务`/`交易所业务`/`场外业务`/`期货业务`/`混合` |
| 清算速度 | number | 0=T+0, 1=T+1 等；多值时为 `-2` |
| 首次交割日 | int | YYYYMMDD；多值时为 `-2` |
| 到期交割日 | int | YYYYMMDD；多值时为 `-2` |
| 回购金额 | number | 同指令金额（回购业务下即回购本金） |
| 回购天数 | number | 明细有则取明细，否则取主表；多值时为 `-1` |
| 交易对手 | string | 对手名称；多对手时为 `"混合"` |
| 对手交易员 | string | 对手交易员姓名 |
| 对手交易员ID | string | 对手交易员ID |
| 渠道 | string | 场外渠道名称 |
| 转入基金代码 | string | 场外基金转入代码；多值时为空格 |
| 分红方式 | string | 场外基金分红方式 |
| 约定号 | string | 约定号 |
| 宽限期 | number | 宽限期天数 |
| 处置标识 | string | 处置标识 |
| 补充条款 | string | 指令摘要2 |
| 三方续作勾选 | string | `"是"` 或 `"否"` |

**出参示例**：

```json
{
  "code": 0,
  "message": "success",
  "body": [
    {
      "指令日期": 20260611,
      "指令编号": 14,
      "修改序号": 1,
      "产品ID": 1003,
      "产品代码": "001909",
      "产品名称": "创金合信货币（招行）",
      "组合ID": 126,
      "组合名称": "缺省组合",
      "指令类型": "个股",
      "委托方向代码": "5",
      "委托方向": "融资回购",
      "价格模式码": "1",
      "指令价格(回购为利率)": 2,
      "指令状态码": "1",
      "委托状态码": "1",
      "成交状态码": "1",
      "指令起始日期": 20260611,
      "指令终止日期": 20260611,
      "指令下达日期": 20260611,
      "指令下达时间": 103116,
      "指令金额": 60000000,
      "成交金额": 0,
      "指令数量": 600000,
      "证券内码": "HGR001YH",
      "证券代码": "R001",
      "证券名称": "R001",
      "市场": "银行间",
      "业务分类": "银行间业务",
      "清算速度": 0,
      "首次交割日": 20260611,
      "到期交割日": 20260612,
      "回购金额": 60000000,
      "回购天数": 1,
      "交易对手": "浦发银行",
      "对手交易员": "pfyhdealer",
      "对手交易员ID": "pfyhdealer",
      "渠道": null,
      "转入基金代码": " ",
      "分红方式": null,
      "约定号": null,
      "宽限期": null,
      "处置标识": null,
      "补充条款": null,
      "三方续作勾选": "否",
      "指令状态": "有效指令",
      "委托状态": "未执行",
      "成交状态": "未成交",
      "价格模式": "限价指令"
    }
  ]
}
```

> **注意**：一条指令可能对应多只证券（如批量指令），此时证券级字段（证券代码/名称/市场等）显示为 `"混合"`，金额/数量为 SUM 聚合值。SQL 涉及 10 表关联 + GROUP BY 聚合，查询务必带 `queryDate` 单日过滤。


---

## 第五章 异常处理

### 5.1 常见错误码

| HTTP 状态码 | 错误信息 | 原因 | 处理方式 |
|-------------|----------|------|----------|
| 200 | - | 请求成功 | - |
| 401 | Unauthorized | API Key 无效或缺失 | 检查 Authorization Header |
| 403 | 写操作接口不允许通过此代理访问 | Nginx 拦截写操作 | 使用直连方式或联系管理员 |
| 403 | 访问被拒绝，此代理仅开放查询接口 | Nginx 拦截非注册路径 | 确认 URL 路径正确 |
| 500 | Internal Server Error | 后端服务异常 | 检查参数或联系管理员 |
| 502/504 | Bad Gateway / Gateway Timeout | 上游服务不可用 | 稍后重试 |

### 5.2 排查步骤

1. **确认 API Key 正确**：检查 Header 格式 `Authorization: Bearer <KEY>`
2. **确认环境 URL**：测试用 `aitest.cjhxfund.com`，生产用 `ai.cjhxfund.com` 或 Nginx `10.203.225.233:8089`
3. **确认接口类型**：API 接口走 `/admin/apiquery/proxy/`，SQL 接口走 `/admin/dataquery/execute/`
4. **确认请求方法**：GET 接口用 `-G`，POST 接口用 `-X POST`
5. **确认 Content-Type**：form 接口用 `application/x-www-form-urlencoded`，json 接口用 `application/json`

---

## 附录

### A. 接口 ID 与微服务映射

| 微服务 | 接口 |
|--------|------|
| repurchase-service（回购服务） | cat_api_trade_0001, 0003~0009, 0015, 0017~0020, **0023**, 0026, 0027, **0029**, 0030~0032 |
| position-api（头寸服务） | cat_api_trade_0002, 0022, **0025** |
| commontrade-service（交易人员管理） | cat_api_trade_0010~0014 |
| tradecommon-api（交易公共服务） | cat_api_trade_0016, **0028** |
| settle-management-service（交收管理服务） | cat_api_trade_0021 |
| tradereport-service（交易报表服务） | cat_api_trade_0024 |

### B. 增量查询模式说明

部分接口采用增量查询模式，通过"游标"参数分批获取数据：

| 接口ID | 游标参数 | 增量字段 | 每批上限 |
|--------|----------|----------|----------|
| cat_sql_trade_0005 | lastRivalId | RIVAL_ID | 5000 |
| cat_sql_trade_0007 | last_security_id | SECURITY_ID | 5000 |
| cat_sql_trade_0008 | last_security_id | SECURITY_ID | 5000 |
| cat_sql_trade_0009 | last_issuer_id | ISSUER_ID | 5000 |
| cat_sql_trade_0014 | last_rival_id + last_security_id | RIVAL_ID + SECURITY_ID（联合） | 10000 |

**使用方法**：
1. 首次查询传 `0`（或较小值）
2. 取返回数据最后一条的主键值
3. 下次查询将该值作为游标参数传入
4. 重复直到返回数据不足一批

### C. 日期参数规范

| 接口类型 | 日期格式 | 示例 |
|----------|----------|------|
| API 接口（form body） | YYYYMMDD 字符串 | `"20260413"` |
| API 接口（json body） | YYYYMMDD 字符串 | `"20260413"` |
| SQL 接口 | YYYYMMDD 整数 | `20260413` |
| 交接接口日期范围 | `YYYY-MM-DD HH:mm:ss` 字符串 | `"2026-03-26 00:00:00"` |

> 注意：SQL 接口日期为**整数类型**（不带引号），API 接口日期为**字符串类型**（带引号）。

### D. 正回购写操作接口的字典值速查

新增正回购询价结果（0027/0030）和待分户数据（0026）时，以下参数为枚举值：

| 参数名 | 值 | 含义 | 适用接口 |
|--------|-----|------|---------|
| clearSpeed | 1 | T+0 | 0027, 0030 |
| clearSpeed | 2 | T+1 | 0027, 0030 |
| repoPriceType | 0 | 不限 | 0026, 0027, 0030 |
| repoPriceType | 1 | R加权 | 0026, 0027, 0030 |
| repoPriceType | 2 | DR加权 | 0026, 0027, 0030 |
| repoPriceType | 3 | 固定利率 | 0026, 0027, 0030 |
| interbankQuoteType | 0 | 未知(交易所) | 0027, 0030 |
| interbankQuoteType | 1 | 对话报价 | 0026, 0027, 0030 |
| interbankQuoteType | 2 | 请求报价 | 0027, 0030 |
| interbankQuoteType | 100 | ideal | 0027, 0030 |
| interbankQuoteType | 101 | XRepo报价 | 0027, 0030 |
| inqBizType | 1 | 银行间债券买卖 | 0027, 0030 |
| inqBizType | 2 | 银行间质押式回购 | 0027, 0030 |
| inqBizType | 3 | 银行间买断式回购 | 0027, 0030 |
| sideCode | 7 | 正回购 | 0027, 0030 |
| mktId | 1 | 上交所A | 0027, 0030 |
| mktId | 2 | 深交所 | 0027, 0030 |
| mktId | 30 | 银行间 | 0027, 0030 |
| bondType | 1 | 信用债 | 0026 |
| bondType | 2 | 国股CD(正) | 0026 |
| bondType | 3 | 利率债(正) | 0026 |
| amountAttribute | 0 | 不限 | 0026 |
| amountAttribute | 1 | 池 | 0026 |
| amountAttribute | 2 | 意向 | 0026 |
| limitMkt | 0 | 全部 | 0026 |
| limitMkt | 2 | 中债 | 0026 |
| limitMkt | 3 | 上清 | 0026 |
| pqType | 0 | 信用烂券排券 | 0026 |
| pqType | 1 | 信用一键排券 | 0026 |
| entrustDirection | 7 | 正回购 | 0026 |
| isPpn / isYx / isEy / isRound | 0 | 否 | 0026 |
| isPpn / isYx / isEy / isRound | 1 | 是 | 0026 |
| ignoreIntentLockQtyCheck | 0 | 不忽略 | 0030 |
| ignoreIntentLockQtyCheck | 1 | 忽略 | 0030 |
| saveDraft | true | 修改后为草稿 | 0030 |
| saveDraft | false | 修改后为有效 | 0030 |
| inqResStatus | 1 | 有效 | 0031, 0032 |
| inqResStatus | 2 | 无效(已撤销) | 0031 |
| inqResStatus | 3 | 草稿 | 0031, 0032 |
| inqResStatus | 8 | 无效(已删除) | 0031 |
| inqResStatus | 9 | 已下达 | 0031 |

> `limitMkt` **没有值 1**，容易误写。

### E. 押品类型字典（HG_PLEDGE_BOND_TYPE）

用于前端押品类型选择表单，与 0026 的 `bondType`（参考押品，仅 3 项）是不同字典：

| 值 | 含义 | 值 | 含义 |
|-----|------|-----|------|
| 1 | 中债利率非浮息 | 8 | 3A国企非永续 |
| 2 | 中债利率 | 9 | AA+国企非永续 |
| 3 | 全部利率 | 10 | 3A国企永续 |
| 4 | 国股CD | 11 | AA+国企永续 |
| 5 | 3A以上CD | 12 | 其他 |
| 6 | 国股二级 | 13 | 上清利率 |
| 7 | 国股永续 | | |

### F. 其他常用字典

| dictId | 对应字段 | 可选值 |
|--------|---------|--------|
| HG_BOND_DISCOUNT_TYPE | 债券打折类型 | 1=按比例×净价 / 2=按比例×min(净价,100) / 4=按净价减 / 5=按min(净价,100)减 / 7=按固定数值 |
| HG_IS_QZ | 是否取整 | 0=不取整, 1=取整 |
| HG_IS_YX | 是否永续 | 0=非永续, 1=永续 |
| HG_IS_EY | 是否二永 | 0=非二永, 1=二永 |
| HG_IS_PPN | 是否PPN | 0=非PPN, 1=PPN |
| HG_PQ_TYPE | 排券方式 | 0=信用烂券排券, 1=信用一键排券 |

---

