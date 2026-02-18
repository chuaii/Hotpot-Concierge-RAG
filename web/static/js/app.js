/**
 * 智能火锅点餐顾问 - 前端逻辑
 */
const chatArea = document.getElementById('chat-area');
const userInput = document.getElementById('user-input');  // 可能不存在（已移除输入栏时）
const sendBtn   = document.getElementById('send-btn');
const form      = document.getElementById('input-bar');

let sessionId = null;

function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addMessage(text, role, source) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  if (role === 'ai' && source && source !== 'system') {
    const tag = document.createElement('span');
    tag.className = `source-tag ${source}`;
    tag.textContent = source === 'rag' ? 'RAG 知识库' : '点餐顾问';
    div.appendChild(tag);
    div.appendChild(document.createElement('br'));
  }
  div.appendChild(document.createTextNode(text));
  chatArea.appendChild(div);
  scrollToBottom();
}

function addOrderCard(json) {
  const card = document.createElement('details');
  card.className = 'order-card';
  card.open = true;
  const summary = document.createElement('summary');
  summary.textContent = '📋 结构化订单（点击展开/收起）';
  const pre = document.createElement('pre');
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
  archivePreviousRecommendCards();
  const card = document.createElement('div');
  card.className = 'order-card recommend-checklist';
  const title = document.createElement('div');
  title.style.fontWeight = '600';
  title.style.color = 'var(--primary)';
  title.style.marginBottom = '4px';
  title.textContent = data.message;
  card.appendChild(title);
  const countEl = document.createElement('div');
  countEl.className = 'recommend-count';
  countEl.style.fontSize = '0.85rem';
  countEl.style.color = 'var(--text-light)';
  countEl.style.marginBottom = '8px';
  card.appendChild(countEl);
  const list = document.createElement('ul');
  list.className = 'recommend-list';
  list.style.margin = '0';
  list.style.paddingLeft = '0';
  list.style.listStyle = 'none';
  list.style.lineHeight = '1.8';
  list.style.fontSize = '0.9rem';
  list.style.minHeight = '420px';
  list.style.maxHeight = '65vh';
  list.style.overflowY = 'auto';
  const allItems = data.all_items || data.items || [];
  allItems.forEach(function(it) {
    const li = document.createElement('li');
    li.style.display = 'flex';
    li.style.alignItems = 'center';
    li.style.gap = '8px';
    li.style.padding = '2px 0';
    li.style.cursor = 'pointer';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = it.checked !== false;
    cb.style.cursor = 'pointer';
    cb.style.accentColor = 'var(--primary)';
    cb.setAttribute('data-id', it.id || '');
    const label = document.createElement('span');
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
  const countEl = cardEl.querySelector('.recommend-count');
  if (!countEl) return;
  const checkboxes = cardEl.querySelectorAll('input[type="checkbox"][data-id]:checked');
  const n = checkboxes.length;
  countEl.textContent = '已选 ' + n + ' 样';
}

function syncCartFromChecklist(cardEl) {
  const sessionIdForCart = cardEl.getAttribute('data-session-id');
  if (!sessionIdForCart) return;
  const checkboxes = cardEl.querySelectorAll('input[type="checkbox"][data-id]');
  const cart = [];
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
  const div = document.createElement('div');
  div.className = 'msg ai typing';
  div.id = 'typing-indicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  chatArea.appendChild(div);
  scrollToBottom();
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
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
  if (!text.trim()) return;

  addMessage(text, 'user');
  if (userInput) userInput.value = '';
  if (sendBtn) sendBtn.disabled = true;
  showTyping();

  try {
    const body = { message: text };
    if (sessionId) body.session_id = sessionId;
    var ctx = context || getChatContext();
    body.num_guests = ctx.num_guests;
    body.allergies = ctx.allergies || [];
    body.broths = (ctx.broths || []).map(function(b) {
      return typeof b === 'object' ? { name_cn: b.name_cn, quantity: b.quantity || 1 } : { name_cn: b, quantity: 1 };
    });

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error('HTTP ' + res.status);

    const data = await res.json();
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

if (form) {
  form.addEventListener('submit', function(e) {
    e.preventDefault();
    if (userInput) sendMessage(userInput.value);
  });
}

document.querySelectorAll('.quick-btn:not(#btn-confirm-order)').forEach(function(btn) {
  btn.addEventListener('click', function() {
    sendMessage(btn.dataset.msg);
  });
});

// 确认下单：需有食材推荐（预选菜单）且已选至少一款锅底
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
btnConfirmOrder.addEventListener('click', function() {
  if (btnConfirmOrder.disabled) return;
  sendMessage(btnConfirmOrder.dataset.msg);
});

// 锅底知识目录（20 种，与菜单一致）
var BROTH_LIST = [
  '姜葱浓汤底', '清新小肥羊汤底', '麻辣小肥羊汤底', '素食汤底', '川味香辣汤底',
  '牛油麻辣汤底', '野生菇菌汤底', '咖喱火锅汤底', '番茄火锅汤底', '啤酒鸭火锅汤底',
  '人参鸡汤底', '药膳乌鸡汤底', '香辣蟹火锅汤底', '香辣牛筋汤底', '香辣牛尾汤底',
  '养颜猪手汤底', '酸菜鱼火锅汤底', '海鲜冬阴功汤底', '鲍鱼火锅汤底', '海参什锦海鲜汤底'
];

var brothTrigger = document.getElementById('broth-trigger');
var brothDropdown = document.getElementById('broth-dropdown');

BROTH_LIST.forEach(function(name) {
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'broth-option';
  btn.textContent = name;
  btn.setAttribute('role', 'option');
  btn.addEventListener('click', function() {
    sendMessage(name + '有什么特点和适合什么人？');
    closeBrothDropdown();
  });
  brothDropdown.appendChild(btn);
});

function toggleBrothDropdown() {
  var isOpen = brothDropdown.classList.toggle('open');
  brothTrigger.classList.toggle('open', isOpen);
  brothTrigger.setAttribute('aria-expanded', isOpen);
}

function closeBrothDropdown() {
  brothDropdown.classList.remove('open');
  brothTrigger.classList.remove('open');
  brothTrigger.setAttribute('aria-expanded', 'false');
}

brothTrigger.addEventListener('click', function(e) {
  e.stopPropagation();
  toggleBrothDropdown();
});

document.addEventListener('click', function(e) {
  if (!e.target.closest('.broth-knowledge-wrap')) closeBrothDropdown();
  if (!e.target.closest('.ingredient-knowledge-wrap')) closeIngredientDropdown();
  if (!e.target.closest('.broth-select-wrap')) closeBrothSelectDropdown();
  if (!e.target.closest('.allergy-wrap')) closeAllergyDropdown();
});

// ---------- 食材信息（67 种，与菜单一致） ----------
var ingredientTrigger = document.getElementById('ingredient-trigger');
var ingredientDropdown = document.getElementById('ingredient-dropdown');

function toggleIngredientDropdown() {
  var isOpen = ingredientDropdown.classList.toggle('open');
  ingredientTrigger.classList.toggle('open', isOpen);
  ingredientTrigger.setAttribute('aria-expanded', isOpen);
}

function closeIngredientDropdown() {
  ingredientDropdown.classList.remove('open');
  ingredientTrigger.classList.remove('open');
  ingredientTrigger.setAttribute('aria-expanded', 'false');
}

fetch('/api/ingredients')
  .then(function(res) { return res.json(); })
  .then(function(data) {
    var list = data.ingredients || [];
    list.forEach(function(it) {
      var nameCn = it.name_cn || '';
      var nameEn = it.name_en || '';
      var label = nameCn + (nameEn ? ' / ' + nameEn : '');
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ingredient-option';
      btn.setAttribute('role', 'option');
      btn.textContent = label;
      btn.addEventListener('click', function() {
        sendMessage(nameCn + '有什么特点和涮煮建议？');
        closeIngredientDropdown();
      });
      ingredientDropdown.appendChild(btn);
    });
  })
  .catch(function() {});

if (ingredientTrigger) {
  ingredientTrigger.addEventListener('click', function(e) {
    e.stopPropagation();
    toggleIngredientDropdown();
  });
}

// ---------- 过敏目录 ----------
var allergyTrigger = document.getElementById('allergy-trigger');
var allergyDropdown = document.getElementById('allergy-dropdown');
var allergyCountEl = document.getElementById('allergy-count');
var allergyInputs = ['allergy-peanut', 'allergy-seafood', 'allergy-gluten'].map(function(id) { return document.getElementById(id); });

function updateAllergyCount() {
  var n = allergyInputs.filter(function(cb) { return cb && cb.checked; }).length;
  allergyCountEl.textContent = '已选 ' + n + ' 项';
}

function toggleAllergyDropdown() {
  var isOpen = allergyDropdown.classList.toggle('open');
  allergyTrigger.classList.toggle('open', isOpen);
  allergyTrigger.setAttribute('aria-expanded', isOpen);
}

function closeAllergyDropdown() {
  allergyDropdown.classList.remove('open');
  allergyTrigger.classList.remove('open');
  allergyTrigger.setAttribute('aria-expanded', 'false');
}

allergyTrigger.addEventListener('click', function(e) {
  e.stopPropagation();
  toggleAllergyDropdown();
});

allergyInputs.forEach(function(cb) {
  if (cb) cb.addEventListener('change', updateAllergyCount);
});
updateAllergyCount();

// ---------- 锅底选择（数量不超过人数） ----------
var brothSelectTrigger = document.getElementById('broth-select-trigger');
var brothSelectDropdown = document.getElementById('broth-select-dropdown');
var brothSelectOptionsEl = document.getElementById('broth-select-options');
var brothSelectCountEl = document.getElementById('broth-select-count');
var guestSelectEl = document.getElementById('guest-select');

function getMaxBroths() {
  return parseInt(guestSelectEl.value, 10) || 2;
}

function getBrothRows() {
  return Array.from(brothSelectOptionsEl.querySelectorAll('.broth-select-row'));
}

function getTotalBrothCount() {
  return getBrothRows().reduce(function(sum, row) {
    var n = parseInt(row.querySelector('.broth-num').textContent, 10) || 0;
    return sum + n;
  }, 0);
}

function updateBrothSelectUI() {
  var max = getMaxBroths();
  var total = getTotalBrothCount();
  brothSelectCountEl.textContent = '已选 ' + total + '/' + max + ' 项';
  getBrothRows().forEach(function(row) {
    var numEl = row.querySelector('.broth-num');
    var n = parseInt(numEl.textContent, 10) || 0;
    var btnMinus = row.querySelector('.btn-minus');
    var btnPlus = row.querySelector('.btn-plus');
    btnMinus.disabled = n <= 0;
    btnPlus.disabled = total >= max;
  });
  if (typeof updateConfirmOrderState === 'function') updateConfirmOrderState();
}

function toggleBrothSelectDropdown() {
  var isOpen = brothSelectDropdown.classList.toggle('open');
  brothSelectTrigger.classList.toggle('open', isOpen);
  brothSelectTrigger.setAttribute('aria-expanded', isOpen);
}

function closeBrothSelectDropdown() {
  brothSelectDropdown.classList.remove('open');
  brothSelectTrigger.classList.remove('open');
  brothSelectTrigger.setAttribute('aria-expanded', 'false');
}

brothSelectTrigger.addEventListener('click', function(e) {
  e.stopPropagation();
  toggleBrothSelectDropdown();
});

BROTH_LIST.forEach(function(name) {
  var row = document.createElement('div');
  row.className = 'broth-select-row';
  var nameSpan = document.createElement('span');
  nameSpan.className = 'broth-name';
  nameSpan.textContent = name;
  var stepper = document.createElement('div');
  stepper.className = 'broth-stepper';
  var btnMinus = document.createElement('button');
  btnMinus.type = 'button';
  btnMinus.className = 'btn-minus';
  btnMinus.setAttribute('aria-label', '减少');
  btnMinus.textContent = '−';
  var numSpan = document.createElement('span');
  numSpan.className = 'broth-num';
  numSpan.textContent = '0';
  var btnPlus = document.createElement('button');
  btnPlus.type = 'button';
  btnPlus.className = 'btn-plus';
  btnPlus.setAttribute('aria-label', '增加');
  btnPlus.textContent = '+';

  btnMinus.addEventListener('click', function() {
    var n = parseInt(numSpan.textContent, 10) || 0;
    if (n > 0) {
      numSpan.textContent = String(n - 1);
      updateBrothSelectUI();
    }
  });
  btnPlus.addEventListener('click', function() {
    var max = getMaxBroths();
    var total = getTotalBrothCount();
    if (total < max) {
      var n = parseInt(numSpan.textContent, 10) || 0;
      numSpan.textContent = String(n + 1);
      updateBrothSelectUI();
    }
  });

  stepper.appendChild(btnMinus);
  stepper.appendChild(numSpan);
  stepper.appendChild(btnPlus);
  row.appendChild(nameSpan);
  row.appendChild(stepper);
  brothSelectOptionsEl.appendChild(row);
});

guestSelectEl.addEventListener('change', function() {
  var max = getMaxBroths();
  var total = getTotalBrothCount();
  if (total <= max) {
    updateBrothSelectUI();
    return;
  }
  var rows = getBrothRows();
  var toReduce = total - max;
  for (var i = rows.length - 1; i >= 0 && toReduce > 0; i--) {
    var numEl = rows[i].querySelector('.broth-num');
    var n = parseInt(numEl.textContent, 10) || 0;
    var deduct = Math.min(n, toReduce);
    if (deduct > 0) {
      numEl.textContent = String(n - deduct);
      toReduce -= deduct;
    }
  }
  updateBrothSelectUI();
});

updateBrothSelectUI();

// ---------- 食材推荐 ----------
document.getElementById('btn-recommend').addEventListener('click', function() {
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

  // 再推荐前先同步当前卡片的勾选状态到后端，确保迁移时用最新数据
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

updateConfirmOrderState();
