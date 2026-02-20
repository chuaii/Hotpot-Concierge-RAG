/**
 * 智能火锅点餐顾问 - 工具函数与常量
 * 工具函数 scrollToBottom、positionDropdownInViewport，常量 BROTH_LIST
 */

/** 锅底知识目录（20 种，与菜单一致） */
var BROTH_LIST = [
  '姜葱浓汤底', '清新小肥羊汤底', '麻辣小肥羊汤底', '素食汤底', '川味香辣汤底',
  '牛油麻辣汤底', '野生菇菌汤底', '咖喱火锅汤底', '番茄火锅汤底', '啤酒鸭火锅汤底',
  '人参鸡汤底', '药膳乌鸡汤底', '香辣蟹火锅汤底', '香辣牛筋汤底', '香辣牛尾汤底',
  '养颜猪手汤底', '酸菜鱼火锅汤底', '海鲜冬阴功汤底', '鲍鱼火锅汤底', '海参什锦海鲜汤底'
];

function scrollToBottom() {
  var chatArea = document.getElementById('chat-area');
  if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
}

/**
 * 将下拉框定位到视窗内，避免超出屏幕。
 * @param {HTMLElement} trigger - 触发按钮
 * @param {HTMLElement} dropdown - 下拉容器
 * @param {{ maxHeight?: number, width?: number }} opts
 */
function positionDropdownInViewport(trigger, dropdown, opts) {
  opts = opts || {};
  var maxH = opts.maxHeight || 320;
  var width = opts.width || 260;
  var gap = 8;
  var pad = 12;

  var tr = trigger.getBoundingClientRect();
  var spaceAbove = tr.top - pad;
  var spaceBelow = window.innerHeight - tr.bottom - gap - pad;

  dropdown.style.position = 'fixed';
  dropdown.style.width = width + 'px';
  dropdown.style.maxHeight = '';

  if (spaceAbove >= 120 && spaceAbove >= spaceBelow) {
    dropdown.style.bottom = (window.innerHeight - tr.top + gap) + 'px';
    dropdown.style.top = 'auto';
    dropdown.style.maxHeight = Math.min(maxH, spaceAbove - gap) + 'px';
  } else {
    dropdown.style.top = (tr.bottom + gap) + 'px';
    dropdown.style.bottom = 'auto';
    dropdown.style.maxHeight = Math.min(maxH, spaceBelow) + 'px';
  }

  var left = tr.left;
  if (left + width > window.innerWidth - pad) left = window.innerWidth - width - pad;
  if (left < pad) left = pad;
  dropdown.style.left = left + 'px';
}
