/**
 * 智能火锅点餐顾问 - 聊天核心逻辑
 * 聊天：addMessage、addOrderCard、addRecommendCard、sendMessage、
 * showTyping、removeTyping、getChatContext 等
 */

var sessionId = null;

function addMessage(text, role, source) {
  var chatArea = document.getElementById('chat-area');
  var div = document.createElement('div');
  div.className = 'msg ' + role;
  if (role === 'ai' && source && source !== 'system') {
    var tag = document.createElement('span');
    tag.className = 'source-tag ' + source;
    tag.textContent = source === 'rag' ? 'RAG 知识库' : '点餐顾问';
    div.appendChild(tag);
    div.appendChild(document.createElement('br'));
  }
  div.appendChild(document.createTextNode(text));
  chatArea.appendChild(div);
  scrollToBottom();
}

function addOrderCard(json) {
  var chatArea = document.getElementById('chat-area');
  var card = document.createElement('details');
  card.className = 'order-card';
  card.open = true;
  var summary = document.createElement('summary');
  summary.textContent = '📋 结构化订单（点击展开/收起）';
  var pre = document.createElement('pre');
  pre.textContent = JSON.stringify(json, null, 2);
  card.appendChild(summary);
  card.appendChild(pre);
  chatArea.appendChild(card);
  scrollToBottom();
}

function archivePreviousRecommendCards() {
  document.querySelectorAll('.recommend-checklist:not(.recommend-checklist--archived)').forEach(function(c) {
    c.classList.add('recommend-checklist--archived');
    c.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.disabled = true; });
  });
}

function addRecommendCard(data) {
  var chatArea = document.getElementById('chat-area');
  archivePreviousRecommendCards();
  var card = document.createElement('div');
  card.className = 'order-card recommend-checklist';
  var title = document.createElement('div');
  title.style.fontWeight = '600';
  title.style.color = 'var(--primary)';
  title.style.marginBottom = '4px';
  title.textContent = data.message;
  card.appendChild(title);
  var countEl = document.createElement('div');
  countEl.className = 'recommend-count';
  countEl.style.fontSize = '0.85rem';
  countEl.style.color = 'var(--text-light)';
  countEl.style.marginBottom = '8px';
  card.appendChild(countEl);
  var list = document.createElement('ul');
  list.className = 'recommend-list';
  list.style.margin = '0';
  list.style.paddingLeft = '0';
  list.style.listStyle = 'none';
  list.style.lineHeight = '1.8';
  list.style.fontSize = '0.9rem';
  list.style.minHeight = '420px';
  list.style.maxHeight = '65vh';
  list.style.overflowY = 'auto';
  var allItems = data.all_items || data.items || [];
  allItems.forEach(function(it) {
    var li = document.createElement('li');
    li.style.display = 'flex';
    li.style.alignItems = 'center';
    li.style.gap = '8px';
    li.style.padding = '2px 0';
    li.style.cursor = 'pointer';
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = it.checked !== false;
    cb.style.cursor = 'pointer';
    cb.style.accentColor = 'var(--primary)';
    cb.setAttribute('data-id', it.id || '');
    var label = document.createElement('span');
    label.textContent = (it.name_cn || it.name_en) + (it.name_en && it.name_cn ? ' / ' + it.name_en : '');
    li.appendChild(cb);
    li.appendChild(label);
    li.addEventListener('click', function(e) {
      if (e.target !== cb) {
        cb.checked = !cb.checked;
        syncCartFromChecklist(card);
      }
    });
    cb.addEventListener('change', function() {
      syncCartFromChecklist(card);
    });
    list.appendChild(li);
  });
  card.appendChild(list);
  card.setAttribute('data-session-id', data.session_id || sessionId || '');
  chatArea.appendChild(card);
  updateRecommendCount(card);
  scrollToBottom();
  if (typeof updateConfirmOrderState === 'function') updateConfirmOrderState();
}

function updateRecommendCount(cardEl) {
  var countEl = cardEl.querySelector('.recommend-count');
  if (!countEl) return;
  var checkboxes = cardEl.querySelectorAll('input[type="checkbox"][data-id]:checked');
  var n = checkboxes.length;
  countEl.textContent = '已选 ' + n + ' 样';
}

function syncCartFromChecklist(cardEl) {
  var sessionIdForCart = cardEl.getAttribute('data-session-id');
  if (!sessionIdForCart) return;
  var checkboxes = cardEl.querySelectorAll('input[type="checkbox"][data-id]');
  var cart = [];
  checkboxes.forEach(function(cb) {
    if (cb.checked && cb.getAttribute('data-id')) {
      cart.push(cb.getAttribute('data-id'));
    }
  });
  updateRecommendCount(cardEl);
  fetch('/api/cart/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionIdForCart, cart: cart })
  })
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (data.ok && sessionIdForCart === sessionId) {
        sessionId = sessionIdForCart;
      }
    })
    .catch(function() {});
}

function showTyping() {
  var chatArea = document.getElementById('chat-area');
  var div = document.createElement('div');
  div.className = 'msg ai typing';
  div.id = 'typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  chatArea.appendChild(div);
  scrollToBottom();
}

function removeTyping() {
  var el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function getChatContext() {
  var numGuests = parseInt(document.getElementById('guest-select').value, 10) || 2;
  var allergies = ['allergy-peanut', 'allergy-seafood', 'allergy-gluten']
    .map(function(id) { return document.getElementById(id); })
    .filter(function(cb) { return cb && cb.checked; })
    .map(function(cb) { return cb.value; });
  var broths = [];
  var rows = document.querySelectorAll('#broth-select-options .broth-select-row');
  rows.forEach(function(row) {
    var nameEl = row.querySelector('.broth-name');
    var numEl = row.querySelector('.broth-num');
    var n = parseInt(numEl && numEl.textContent, 10) || 0;
    if (n > 0 && nameEl) {
      broths.push({ name_cn: nameEl.textContent.trim(), quantity: n });
    }
  });
  return { num_guests: numGuests, allergies: allergies, broths: broths };
}

async function sendMessage(text, context) {
  var userInput = document.getElementById('user-input');
  var sendBtn = document.getElementById('send-btn');
  if (!text.trim()) return;

  addMessage(text, 'user');
  if (userInput) userInput.value = '';
  if (sendBtn) sendBtn.disabled = true;
  showTyping();

  try {
    var body = { message: text };
    if (sessionId) body.session_id = sessionId;
    var ctx = context || getChatContext();
    body.num_guests = ctx.num_guests;
    body.allergies = ctx.allergies || [];
    body.broths = (ctx.broths || []).map(function(b) {
      return typeof b === 'object' ? { name_cn: b.name_cn, quantity: b.quantity || 1 } : { name_cn: b, quantity: 1 };
    });

    var res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error('HTTP ' + res.status);

    var data = await res.json();
    sessionId = data.session_id;

    removeTyping();
    addMessage(data.reply, 'ai', data.source);

    if (data.order_json) {
      addOrderCard(data.order_json);
    }
  } catch (err) {
    removeTyping();
    addMessage('网络错误：' + err.message + '，请稍后重试。', 'system');
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    if (userInput) userInput.focus();
  }
}
