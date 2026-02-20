/**
 * 智能火锅点餐顾问 - 主入口
 * 表单、快捷按钮、确认下单、食材推荐的按钮事件绑定
 */

var form = document.getElementById('input-bar');
var userInput = document.getElementById('user-input');
var sendBtn = document.getElementById('send-btn');

// 表单提交
if (form) {
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    if (userInput) sendMessage(userInput.value);
  });
}

// 快捷按钮
document.querySelectorAll('.quick-btn:not(#btn-confirm-order)').forEach(function(btn) {
  btn.addEventListener('click', function() {
    sendMessage(btn.dataset.msg);
  });
});

// 确认下单
var btnConfirmOrder = document.getElementById('btn-confirm-order');
function updateConfirmOrderState() {
  var hasRecommend = !!document.querySelector('.recommend-checklist');
  var hasBroth = getTotalBrothCount() > 0;
  btnConfirmOrder.disabled = !hasRecommend || !hasBroth;
  var tips = [];
  if (!hasRecommend) tips.push('点击「食材推荐」生成预选菜单');
  if (!hasBroth) tips.push('在「锅底选择」中至少选择一款锅底');
  btnConfirmOrder.title = tips.length ? '请先：' + tips.join('；') : '';
}
if (btnConfirmOrder) {
  btnConfirmOrder.addEventListener('click', function() {
    if (btnConfirmOrder.disabled) return;
    sendMessage(btnConfirmOrder.dataset.msg);
  });
}

// 食材推荐
var btnRecommend = document.getElementById('btn-recommend');
if (btnRecommend) {
  btnRecommend.addEventListener('click', function() {
    var numGuests = parseInt(document.getElementById('guest-select').value, 10) || 2;
    var allergies = allergyInputs.filter(function(cb) { return cb && cb.checked; }).map(function(cb) { return cb.value; });
    var userMsg = '请根据' + numGuests + '人';
    if (allergies.length) userMsg += '，' + allergies.join('、') + '过敏';
    userMsg += '，推荐一份预选食材（含肉、海鲜、蔬菜、豆制品、主食）。';
    addMessage(userMsg, 'user');

    if (sendBtn) sendBtn.disabled = true;
    showTyping();

    var body = { num_guests: numGuests, allergies: allergies };
    if (sessionId) body.session_id = sessionId;

    var latestCard = document.querySelector('.recommend-checklist:not(.recommend-checklist--archived)');
    var syncPromise = Promise.resolve();
    if (latestCard && sessionId) {
      var cart = [];
      latestCard.querySelectorAll('input[type="checkbox"][data-id]').forEach(function(cb) {
        if (cb.checked && cb.getAttribute('data-id')) cart.push(cb.getAttribute('data-id'));
      });
      syncPromise = fetch('/api/cart/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, cart: cart })
      }).then(function(r) { return r.json(); }).then(function() {});
    }
    syncPromise.then(function() {
      return fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        removeTyping();
        sessionId = data.session_id;
        addMessage(data.message, 'ai', 'concierge');
        addRecommendCard(data);
      })
      .catch(function(err) {
        removeTyping();
        addMessage('获取推荐失败：' + (err.message || err), 'system');
      })
      .finally(function() {
        if (sendBtn) sendBtn.disabled = false;
        if (userInput) userInput.focus();
      });
  });
}

updateConfirmOrderState();
