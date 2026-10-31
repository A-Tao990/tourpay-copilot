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
 "cannot_refund": {
  "en": "Order {oid} cannot be refunded (status {status}). Only completed payments can be refunded.", "zh": "订单 {oid} 无法退款（状态 {status}），只有已完成的付款才能退款。",
  "vi": "Đơn {oid} không thể hoàn tiền (trạng thái {status}). Chỉ thanh toán đã hoàn tất mới được hoàn tiền."},
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
