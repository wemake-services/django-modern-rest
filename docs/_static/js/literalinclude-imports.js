/* Hide/show import lines in one code block and keep full copy. */
(function () {
  'use strict';

  const WRAPPER_SELECTOR = '.literal-block-wrapper.imports-inline-enabled';

  function getMainPre(wrapper) {
    return wrapper.querySelector('.highlight pre');
  }

  function getToggleButton(wrapper) {
    return wrapper.querySelector('.imports-spoiler-toggle');
  }

  function normalizeTrailingNewline(text) {
    return text.endsWith('\n') ? text.slice(0, -1) : text;
  }

  function getImportsStartLine(wrapper) {
    const toggleContainer = wrapper.querySelector('.imports-inline-spoiler');
    if (!toggleContainer) {
      return null;
    }

    const raw = toggleContainer.getAttribute('data-imports-from-line');
    const value = raw ? Number.parseInt(raw, 10) : Number.NaN;
    return Number.isFinite(value) && value > 1 ? value : null;
  }

  function setToggleLabel(wrapper, expanded) {
    const button = getToggleButton(wrapper);
    if (!button) {
      return;
    }

    const collapsedTitle =
      button.getAttribute('data-collapsed-title') || 'Show imports';
    const expandedTitle =
      button.getAttribute('data-expanded-title') || 'Hide imports';
    button.textContent = expanded ? expandedTitle : collapsedTitle;
    button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function syncToggleBackground(wrapper) {
    const button = getToggleButton(wrapper);
    const pre = getMainPre(wrapper);
    if (!button || !pre) {
      return;
    }

    button.style.backgroundColor = window.getComputedStyle(pre).backgroundColor;
  }

  function markImportLines(wrapper) {
    const pre = getMainPre(wrapper);
    const startLine = getImportsStartLine(wrapper);
    if (!pre || !startLine) {
      return;
    }

    pre.querySelectorAll(':scope > span[data-line]').forEach((lineNode) => {
      const rawLine = lineNode.getAttribute('data-line');
      const lineNumber = rawLine ? Number.parseInt(rawLine, 10) : Number.NaN;
      if (Number.isFinite(lineNumber) && lineNumber < startLine) {
        lineNode.classList.add('imports-hidden-line');
      }
    });
  }

  function getPreLineText(preNode) {
    const lineNodes = preNode.querySelectorAll(':scope > span[data-line]');
    if (!lineNodes.length) {
      return normalizeTrailingNewline(preNode.textContent || '');
    }

    return Array.from(lineNodes)
      .map((lineNode) => {
        const clone = lineNode.cloneNode(true);
        clone.querySelectorAll('.linenos').forEach((lineno) => lineno.remove());
        return normalizeTrailingNewline(clone.textContent || '');
      })
      .join('\n');
  }

  function writeToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }

    return new Promise((resolve, reject) => {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      const ok = document.execCommand('copy');
      textarea.remove();
      if (ok) {
        resolve();
      } else {
        reject(new Error('copy failed'));
      }
    });
  }

  function showCopyStatus(button, ok) {
    const old = button.getAttribute('data-tooltip');
    button.setAttribute('data-tooltip', ok ? 'Copied!' : 'Failed to copy');
    window.setTimeout(() => {
      if (old) {
        button.setAttribute('data-tooltip', old);
      }
    }, 1800);
  }

  function handleToggleClick(event) {
    const button = event.target.closest
      ? event.target.closest('.imports-spoiler-toggle')
      : null;
    if (!button) {
      return;
    }

    const wrapper = button.closest(WRAPPER_SELECTOR);
    if (!wrapper) {
      return;
    }

    const expanded = wrapper.classList.toggle('imports-expanded');
    setToggleLabel(wrapper, expanded);
  }

  function handleCopyClick(event) {
    const button = event.target.closest
      ? event.target.closest('button.copybtn')
      : null;
    if (!button) {
      return;
    }

    const targetSelector = button.getAttribute('data-clipboard-target');
    const targetPre = targetSelector
      ? document.querySelector(targetSelector)
      : null;
    const wrapper = targetPre ? targetPre.closest(WRAPPER_SELECTOR) : null;
    const pre = wrapper ? getMainPre(wrapper) : null;
    if (!pre) {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    writeToClipboard(normalizeTrailingNewline(getPreLineText(pre)))
      .then(() => showCopyStatus(button, true))
      .catch(() => showCopyStatus(button, false));
  }

  function bootstrap() {
    document.querySelectorAll(WRAPPER_SELECTOR).forEach((wrapper) => {
      markImportLines(wrapper);
      wrapper.classList.remove('imports-expanded');
      setToggleLabel(wrapper, false);
      syncToggleBackground(wrapper);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }

  document.addEventListener('click', handleToggleClick, true);
  document.addEventListener('click', handleCopyClick, true);
})();
