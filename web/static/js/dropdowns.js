/**
 * 智能火锅点餐顾问 - 各类下拉组件
 * 锅底知识、食材信息、过敏、锅底选择
 */

// ---------- 锅底知识 ----------
var brothTrigger = document.getElementById('broth-trigger');
var brothDropdown = document.getElementById('broth-dropdown');

function toggleBrothDropdown() {
  var isOpen = brothDropdown.classList.toggle('open');
  brothTrigger.classList.toggle('open', isOpen);
  brothTrigger.setAttribute('aria-expanded', isOpen);
  if (isOpen) positionDropdownInViewport(brothTrigger, brothDropdown, { maxHeight: 280 });
}

function closeBrothDropdown() {
  brothDropdown.classList.remove('open');
  brothTrigger.classList.remove('open');
  brothTrigger.setAttribute('aria-expanded', 'false');
}

if (brothTrigger && brothDropdown) {
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

  brothTrigger.addEventListener('click', function(e) {
    e.stopPropagation();
    toggleBrothDropdown();
  });
}

// ---------- 食材信息 ----------
var ingredientTrigger = document.getElementById('ingredient-trigger');
var ingredientDropdown = document.getElementById('ingredient-dropdown');

function toggleIngredientDropdown() {
  var isOpen = ingredientDropdown.classList.toggle('open');
  ingredientTrigger.classList.toggle('open', isOpen);
  ingredientTrigger.setAttribute('aria-expanded', isOpen);
  if (isOpen) positionDropdownInViewport(ingredientTrigger, ingredientDropdown, { maxHeight: 320 });
}

function closeIngredientDropdown() {
  ingredientDropdown.classList.remove('open');
  ingredientTrigger.classList.remove('open');
  ingredientTrigger.setAttribute('aria-expanded', 'false');
}

if (ingredientTrigger && ingredientDropdown) {
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

  ingredientTrigger.addEventListener('click', function(e) {
    e.stopPropagation();
    toggleIngredientDropdown();
  });
}

// ---------- 过敏 ----------
var allergyTrigger = document.getElementById('allergy-trigger');
var allergyDropdown = document.getElementById('allergy-dropdown');
var allergyCountEl = document.getElementById('allergy-count');
var allergyInputs = ['allergy-peanut', 'allergy-seafood', 'allergy-gluten'].map(function(id) { return document.getElementById(id); });

function updateAllergyCount() {
  var n = allergyInputs.filter(function(cb) { return cb && cb.checked; }).length;
  if (allergyCountEl) allergyCountEl.textContent = '已选 ' + n + ' 项';
}

function toggleAllergyDropdown() {
  var isOpen = allergyDropdown.classList.toggle('open');
  allergyTrigger.classList.toggle('open', isOpen);
  allergyTrigger.setAttribute('aria-expanded', isOpen);
  if (isOpen) positionDropdownInViewport(allergyTrigger, allergyDropdown, { maxHeight: 180, width: 200 });
}

function closeAllergyDropdown() {
  allergyDropdown.classList.remove('open');
  allergyTrigger.classList.remove('open');
  allergyTrigger.setAttribute('aria-expanded', 'false');
}

if (allergyTrigger) {
  allergyTrigger.addEventListener('click', function(e) {
    e.stopPropagation();
    toggleAllergyDropdown();
  });
}
allergyInputs.forEach(function(cb) {
  if (cb) cb.addEventListener('change', updateAllergyCount);
});
if (allergyCountEl) updateAllergyCount();

// ---------- 锅底选择 ----------
var brothSelectTrigger = document.getElementById('broth-select-trigger');
var brothSelectDropdown = document.getElementById('broth-select-dropdown');
var brothSelectOptionsEl = document.getElementById('broth-select-options');
var brothSelectCountEl = document.getElementById('broth-select-count');
var guestSelectEl = document.getElementById('guest-select');

function getMaxBroths() {
  return parseInt(guestSelectEl && guestSelectEl.value, 10) || 2;
}

function getBrothRows() {
  return Array.from((brothSelectOptionsEl || {}).querySelectorAll('.broth-select-row') || []);
}

function getTotalBrothCount() {
  return getBrothRows().reduce(function(sum, row) {
    var numEl = row.querySelector('.broth-num');
    var n = parseInt(numEl && numEl.textContent, 10) || 0;
    return sum + n;
  }, 0);
}

function updateBrothSelectUI() {
  if (!brothSelectCountEl || !brothSelectOptionsEl) return;
  var max = getMaxBroths();
  var total = getTotalBrothCount();
  brothSelectCountEl.textContent = '已选 ' + total + '/' + max + ' 项';
  getBrothRows().forEach(function(row) {
    var numEl = row.querySelector('.broth-num');
    var n = parseInt(numEl && numEl.textContent, 10) || 0;
    var btnMinus = row.querySelector('.btn-minus');
    var btnPlus = row.querySelector('.btn-plus');
    if (btnMinus) btnMinus.disabled = n <= 0;
    if (btnPlus) btnPlus.disabled = total >= max;
  });
  if (typeof updateConfirmOrderState === 'function') updateConfirmOrderState();
}

function toggleBrothSelectDropdown() {
  var isOpen = brothSelectDropdown.classList.toggle('open');
  brothSelectTrigger.classList.toggle('open', isOpen);
  brothSelectTrigger.setAttribute('aria-expanded', isOpen);
  if (isOpen) positionDropdownInViewport(brothSelectTrigger, brothSelectDropdown, { maxHeight: 340 });
}

function closeBrothSelectDropdown() {
  brothSelectDropdown.classList.remove('open');
  brothSelectTrigger.classList.remove('open');
  brothSelectTrigger.setAttribute('aria-expanded', 'false');
}

if (brothSelectTrigger && brothSelectOptionsEl) {
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

  if (guestSelectEl) {
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
        var n = parseInt(numEl && numEl.textContent, 10) || 0;
        var deduct = Math.min(n, toReduce);
        if (deduct > 0) {
          numEl.textContent = String(n - deduct);
          toReduce -= deduct;
        }
      }
      updateBrothSelectUI();
    });
  }

  updateBrothSelectUI();
}

// 全局点击关闭下拉
document.addEventListener('click', function(e) {
  if (!e.target.closest('.broth-knowledge-wrap') && brothDropdown) closeBrothDropdown();
  if (!e.target.closest('.ingredient-knowledge-wrap') && ingredientDropdown) closeIngredientDropdown();
  if (!e.target.closest('.broth-select-wrap') && brothSelectDropdown) closeBrothSelectDropdown();
  if (!e.target.closest('.allergy-wrap') && allergyDropdown) closeAllergyDropdown();
});
