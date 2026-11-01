"""Reply templates in English / Chinese / Vietnamese. (Vietnamese was written with AI help: needs native review.)"""
T = {
 "quote": {
  "en": "{vnd} VND is about {value} {cur} (1 {cur} = {rate} VND, {src} rate). PayPal adds its own conversion spread and fees.",
  "zh": "{vnd} 越南盾约合 {value} {cur}（1 {cur} = {rate} 越南盾，{src}汇率）。PayPal 还会收取自己的换汇差价和手续费。",
  "vi": "{vnd} VND khoảng {value} {cur} (1 {cur} = {rate} VND, tỷ giá {src}). PayPal áp dụng thêm chênh lệch tỷ giá và phí riêng."},
 "created": {
  "en": "Payment request created: {vnd} VND = {value} {cur}. Order {oid}. Open this link to pay with PayPal: {url}",
  "zh": "已创建收款请求：{vnd} 越南盾 = {value} {cur}。订单号 {oid}。请打开链接用 PayPal 付款：{url}",
  "vi": "Đã tạo yêu cầu thanh toán: {vnd} VND = {value} {cur}. Mã đơn {oid}. Mở liên kết để thanh toán bằng PayPal: {url}"},
 "status": {
  "en": "Order {oid} is {status}.", "zh": "订单 {oid} 当前状态：{status}。", "vi": "Đơn {oid} hiện ở trạng thái: {status}."},
 "captured": {
  "en": "Payment received. Order {oid} is {status}. Capture id {cap}.", "zh": "已收到付款。订单 {oid} 状态：{status}，捕获编号 {cap}。",
  "vi": "Đã nhận thanh toán. Đơn {oid}: {status}. Mã ghi nhận {cap}."},
 "need_approval": {
  "en": "Order {oid} is still {status}. The payer must approve it on PayPal first.", "zh": "订单 {oid} 仍是 {status}，需要付款人先在 PayPal 上确认。",
  "vi": "Đơn {oid} vẫn ở trạng thái {status}. Người trả tiền cần xác nhận trên PayPal trước."},
 "options": {
  "en": "Common ways tourists pay in Vietnam: cash (VND), international cards at larger venues, and local bank-app QR payments (VietQR) if you hold a Vietnamese bank account. PayPal is not widely accepted by small merchants, and cryptocurrency is not legal tender for payments in Vietnam (only licensed providers may convert it). General information, not legal advice.",
  "zh": "游客在越南常见的付款方式：现金（越南盾）、较大场所可刷国际银行卡、持有越南银行账户时可用本地银行 App 的二维码（VietQR）。小商家普遍不接受 PayPal；加密货币在越南不是合法支付工具，只有持牌机构才能兑换。以上为一般信息，不是法律意见。",
  "vi": "Các cách du khách thường thanh toán tại Việt Nam: tiền mặt (VND), thẻ quốc tế tại nơi lớn, và QR ngân hàng (VietQR) nếu có tài khoản ngân hàng Việt Nam. PayPal chưa được các cửa hàng nhỏ chấp nhận rộng rãi; tiền mã hóa không phải phương tiện thanh toán hợp pháp tại Việt Nam (chỉ tổ chức được cấp phép mới được quy đổi). Thông tin chung, không phải tư vấn pháp lý."},
 "refunded": {
  "en": "Refund issued for order {oid}: {value} {cur}. Refund id {rid}.", "zh": "订单 {oid} 已退款：{value} {cur}。退款编号 {rid}。",
  "vi": "Đã hoàn tiền đơn {oid}: {value} {cur}. Mã hoàn tiền {rid}."},
 "refund_confirm": {
  "en": "Refund request: order {oid}, {value} {cur} (full amount, back to the payer). NOTHING has been refunded yet. Reply 'confirm refund' within {secs} seconds to proceed; anything else cancels.",
  "zh": "退款申请：订单 {oid}，{value} {cur}（全额退回付款人）。目前尚未退款。请在 {secs} 秒内回复“确认退款”继续；回复其他内容将取消。",
  "vi": "Yêu cầu hoàn tiền: đơn {oid}, {value} {cur} (hoàn toàn bộ cho người trả). CHƯA hoàn tiền. Trả lời 'xác nhận hoàn tiền' trong {secs} giây để tiếp tục; trả lời nội dung khác sẽ hủy."},
 "refund_declined": {
  "en": "OK - no refund was made. Nothing was changed.", "zh": "好的，没有退款，一切保持不变。", "vi": "Được, không hoàn tiền. Không có gì thay đổi."},
 "refund_info": {
  "en": "Nothing was refunded. Only COMPLETED payments can be refunded, always the full amount back to the payer. To start one, say 'refund' or 'refund <order id>'; I will show the order and amount and ask you to confirm first.",
  "zh": "没有进行任何退款。只有状态为 COMPLETED 的付款可以退款，且为全额退回付款人。要发起退款，请说“退款”或“退款 <订单号>”；我会先显示订单和金额，等你确认后才会执行。",
  "vi": "Chưa hoàn tiền gì cả. Chỉ thanh toán COMPLETED mới được hoàn tiền, luôn hoàn toàn bộ cho người trả. Để bắt đầu, hãy nói 'hoàn tiền' hoặc 'hoàn tiền <mã đơn>'; tôi sẽ hiển thị đơn và số tiền rồi hỏi bạn xác nhận trước."},
 "refund_cancelled": {
  "en": "Refund cancelled - nothing was refunded.", "zh": "退款已取消，没有退款。", "vi": "Đã hủy hoàn tiền - chưa hoàn tiền gì."},
 "refund_none_pending": {
  "en": "There is no refund waiting for confirmation (none requested, or it expired or changed). Nothing was refunded. Say 'refund' to start again.",
  "zh": "当前没有待确认的退款（未发起、已过期或已变更），没有退款。需要的话请重新说“退款”。",
  "vi": "Hiện không có yêu cầu hoàn tiền nào chờ xác nhận (chưa yêu cầu, đã hết hạn hoặc đã thay đổi). Chưa hoàn tiền gì. Hãy nói 'hoàn tiền' để bắt đầu lại."},
 "capture_declined": {
  "en": "OK - I did not record any payment. Nothing was changed.", "zh": "好的，没有确认收款，一切保持不变。", "vi": "Được, tôi không ghi nhận thanh toán. Không có gì thay đổi."},
 "capture_info": {
  "en": "Nothing was captured. Say 'confirm payment' (after the payer approved on PayPal) to record the payment; 'status' shows where an order stands.",
  "zh": "没有确认任何收款。付款人在 PayPal 批准后，说“确认收款”即可记录付款；说“状态”可查看订单进度。",
  "vi": "Chưa ghi nhận thanh toán nào. Sau khi người trả đã xác nhận trên PayPal, hãy nói 'xác nhận thanh toán' để ghi nhận; 'trạng thái' cho biết tình trạng đơn."},
 "cannot_refund": {
  "en": "Order {oid} cannot be refunded (status {status}). Only completed payments can be refunded.", "zh": "订单 {oid} 无法退款（状态 {status}），只有已完成的付款才能退款。",
  "vi": "Đơn {oid} không thể hoàn tiền (trạng thái {status}). Chỉ thanh toán đã hoàn tất mới được hoàn tiền."},
 "too_small": {
  "en": "That amount is too small to charge ({vnd} VND converts to {value} {cur}).", "zh": "金额太小，无法收款（{vnd} 越南盾折合 {value} {cur}）。",
  "vi": "Số tiền quá nhỏ để thu ({vnd} VND quy đổi thành {value} {cur})."},
 "bad_currency": {
  "en": "Sorry, {code} is not supported in this demo. Please choose one of: {supported}.", "zh": "抱歉，本演示不支持 {code}。请从以下币种中选择：{supported}。",
  "vi": "Xin lỗi, bản demo chưa hỗ trợ {code}. Vui lòng chọn một trong: {supported}."},
 "negative": {
  "en": "Amounts must be positive. Please tell me the bill total in VND.", "zh": "金额必须是正数，请告诉我越南盾账单总额。",
  "vi": "Số tiền phải là số dương. Vui lòng cho tôi tổng hóa đơn bằng VND."},
 "usd_fallback": {
  "en": "That currency is not supported here, so I used USD. ", "zh": "不支持该币种，已改用美元。", "vi": "Loại tiền này chưa được hỗ trợ nên tôi dùng USD. "},
 "help": {
  "en": "Tell me an amount in VND and a currency, e.g. '3 x 45k + 80k, pay in USD'. I can quote it, create a PayPal (sandbox) payment link, check its status and capture it. Ask 'how can I pay' for payment options.",
  "zh": "告诉我越南盾金额和币种，例如“3 x 45k + 80k，用美元付”。我可以报价、创建 PayPal（沙盒）付款链接、查询状态并确认收款。问“怎么付款”可以了解付款方式。",
  "vi": "Hãy cho tôi số tiền VND và loại tiền, ví dụ '3 x 45k + 80k, thanh toán bằng USD'. Tôi có thể báo giá, tạo liên kết thanh toán PayPal (sandbox), kiểm tra và ghi nhận thanh toán. Hỏi 'làm sao để thanh toán' để xem các cách thanh toán."},
 "too_big": {
  "en": "That amount is above the demo limit ({limit} VND).", "zh": "金额超过演示上限（{limit} 越南盾）。", "vi": "Số tiền vượt quá giới hạn demo ({limit} VND)."},
 "error": {
  "en": "Sorry, something went wrong: {err}", "zh": "抱歉，出错了：{err}", "vi": "Xin lỗi, đã xảy ra lỗi: {err}"},
 "receipt": {
  "en": "RECEIPT (SANDBOX - no real money)\nOrder: {oid}\nItems total: {vnd} VND\nCharged: {value} {cur}\nStatus: {status}\nRate: 1 {cur} = {rate} VND ({src})",
  "zh": "收据（沙盒，非真实资金）\n订单：{oid}\n合计：{vnd} 越南盾\n收款：{value} {cur}\n状态：{status}\n汇率：1 {cur} = {rate} 越南盾（{src}）",
  "vi": "BIÊN LAI (SANDBOX - không phải tiền thật)\nĐơn: {oid}\nTổng: {vnd} VND\nĐã thu: {value} {cur}\nTrạng thái: {status}\nTỷ giá: 1 {cur} = {rate} VND ({src})"},
}
def t(key, lang, **kw):
    return T[key].get(lang, T[key]["en"]).format(**kw)
