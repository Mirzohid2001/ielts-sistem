/**
 * Admin panel - Savol turi bo'yicha maydonlarni ko'rsatish/yashirish
 */
(function() {
    'use strict';

    var MCQ_TYPES = ['mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given'];
    var ONLY_AB = ['true_false'];           // faqat A va B (True/False)
    var ONLY_ABC = ['true_false_not_given', 'yes_no_not_given'];  // A, B, C — D kerak emas
    /* Barcha MCQ bo'lmagan turlar: Summary Completion (Reading), Notes, Matching, Essay va b. — to'ldirish bloki */
    var FILL_TYPES = ['fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer'];
    var MATCHING_TYPES = ['matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification', 'list_selection'];
    var OTHER_FILL_BLOCK_TYPES = ['essay'];  // Essay: Part (Task 1/2), Instruction

    function showMcq(qType) { return qType && MCQ_TYPES.indexOf(qType) >= 0; }
    function showJson(qType) {
        if (!qType) return false;
        return FILL_TYPES.indexOf(qType) >= 0 || MATCHING_TYPES.indexOf(qType) >= 0 || OTHER_FILL_BLOCK_TYPES.indexOf(qType) >= 0 || !showMcq(qType);
    }
    function showOptionC(qType) { return qType === 'mcq' || ONLY_ABC.indexOf(qType) >= 0; }  // True/False da C ham yashirin
    function showOptionD(qType) { return qType === 'mcq'; }  // D faqat MCQ da

    function toggleFieldset(fieldset, show) {
        if (!fieldset) return;
        var el = typeof fieldset === 'string' ? document.querySelector(fieldset) : fieldset;
        if (el) {
            el.style.display = show ? 'block' : 'none';
            el.classList.toggle('question-type-mcq-hidden', !show);
        }
    }

    /** Input atrofidagi "qator" — Django admin: .form-row yoki .fieldBox ichidagi eng yaqin blok */
    function findRowForInput(input) {
        if (!input) return null;
        var el = input.parentElement;
        for (var i = 0; i < 12 && el; i++) {
            if (el === document.body) break;
            var c = el.getAttribute && el.getAttribute('class');
            if (c && (c.indexOf('form-row') !== -1 || c.indexOf('fieldBox') !== -1 || c.indexOf('form-group') !== -1 || c === 'module')) return el;
            if (el.tagName === 'TR') return el;
            if (el.tagName === 'DIV' && c && /field-|form|row/.test(c)) return el;
            el = el.parentElement;
        }
        return input.parentElement && input.parentElement.parentElement ? input.parentElement.parentElement : input.parentElement;
    }

    /** Barcha option inputlari bo'lgan eng kichik ajdod (Variant A-D bloki) */
    function findOptionsBlock(container) {
        var sel = 'input[name*="option_a"], input[name*="option_b"], input[name*="option_c"], input[name*="option_d"]';
        var opts = container.querySelectorAll(sel);
        if (opts.length === 0) return null;
        var first = opts[0];
        var p = first.parentElement;
        while (p && p !== document.body && p !== container) {
            if (p.querySelectorAll(sel).length === opts.length) return p;
            p = p.parentElement;
        }
        return findRowForInput(first);
    }

    function toggleFormRow(input, show) {
        if (!input) return;
        var row = findRowForInput(input);
        if (row) {
            row.style.display = show ? '' : 'none';
            row.classList.toggle('question-type-row-hidden', !show);
        }
    }

    /** True/False/Not Given da C yoki D ustunini yashirish: bitta qatorda 4 ustun bo'lsa faqat ustunni, aks holda butun qatorni. */
    function toggleOptionColumn(input, show) {
        if (!input) return;
        var row = input.closest('.form-row');
        var wrap = input.closest('div');
        var optionCount = row ? row.querySelectorAll('[name*="option_a"], [name*="option_b"], [name*="option_c"], [name*="option_d"]').length : 0;
        if (row && optionCount > 1 && wrap && wrap.parentNode === row) {
            wrap.style.display = show ? '' : 'none';
        } else {
            toggleFormRow(input, show);
        }
    }

    var FILL_NOTE_TYPES = ['notes_completion', 'summary_completion', 'sentence_completion', 'table_completion', 'fill_blank', 'short_answer'];
    var QUESTION_TEXT_HELP = {
        fill_notes: "Matnda bo'sh joylar uchun [1], [2], [3] yozing. Misol: 'Accommodation: [1] Hotel on George Street. Cost: £ [2]'. Keyin 'To'g'ri javoblar' maydonida: central,85",
        essay: "To'liq task matni. Masalan: 'You should spend about 20 minutes on this task. Write at least 150 words...' va savol/diagram tavsifi."
    };

    function updateQuestionTextHelp(container, qType) {
        var textarea = container.querySelector('textarea[name*="question_text"]');
        if (!textarea) return;
        var helpSpan = container.querySelector('.question-text-help-hint');
        if (FILL_NOTE_TYPES.indexOf(qType) >= 0 || qType === 'essay') {
            if (!helpSpan) {
                helpSpan = document.createElement('p');
                helpSpan.className = 'help question-text-help-hint';
                helpSpan.style.marginTop = '4px';
                helpSpan.style.color = '#666';
                helpSpan.style.fontSize = '12px';
                textarea.parentNode.appendChild(helpSpan);
            }
            helpSpan.textContent = (qType === 'essay' ? QUESTION_TEXT_HELP.essay : QUESTION_TEXT_HELP.fill_notes);
            helpSpan.style.display = '';
        } else if (helpSpan) {
            helpSpan.style.display = 'none';
        }
    }

    function ensureShartDiv(container) {
        var select = container.querySelector('select[name*="question_type"]');
        if (!select || !window.QUESTION_TYPE_RULES) return null;
        var shartDiv = container.querySelector('.question-type-shart-box');
        if (!shartDiv) {
            shartDiv = document.createElement('div');
            shartDiv.className = 'question-type-shart-box';
            shartDiv.style.marginTop = '8px';
            shartDiv.style.marginBottom = '12px';
            shartDiv.style.padding = '10px 12px';
            shartDiv.style.background = '#f0f8ff';
            shartDiv.style.borderLeft = '4px solid #79aec8';
            shartDiv.style.borderRadius = '0 6px 6px 0';
            shartDiv.style.fontSize = '13px';
            shartDiv.style.color = '#264b56';
            var row = select.closest('.form-row') || select.parentElement;
            if (row && row.parentNode) row.parentNode.insertBefore(shartDiv, row.nextSibling);
            else container.appendChild(shartDiv);
        }
        return shartDiv;
    }

    function updateShartForType(container, qType) {
        var shartDiv = ensureShartDiv(container);
        if (!shartDiv || !window.QUESTION_TYPE_RULES) return;
        var text = window.QUESTION_TYPE_RULES[qType] || '';
        if (text) {
            shartDiv.textContent = '📋 Shart (bu savol turi uchun): ' + text;
            shartDiv.style.display = 'block';
        } else {
            shartDiv.style.display = 'none';
        }
    }

    function toggleByQuestionType(container) {
        var select = container.querySelector('select[name*="question_type"]');
        if (!select) return;

        var qType = select.value;
        var showMcqFields = showMcq(qType);
        var showJsonFields = showJson(qType);

        updateShartForType(container, qType);
        updateQuestionTextHelp(container, qType);

        // Asosiy form (fieldsets) — faqat MCQ/T-F/T-F NG/Y-N NG da «Variantlar» bloki, qolgan turlarda yopiq
        var mcqFieldset = container.querySelector('.question-mcq-fields');
        var fillFieldset = container.querySelector('.question-fill-fields');
        if (!mcqFieldset) {
            var optA = container.querySelector('input[name*="option_a"]');
            if (optA) mcqFieldset = optA.closest('fieldset');
        }
        if (!mcqFieldset) {
            var maxChoices = container.querySelector('select[name*="max_choices"], [data-role="qt-mcq"]');
            if (maxChoices) mcqFieldset = maxChoices.closest('fieldset');
        }
        if (!fillFieldset) {
            var partInp = container.querySelector('input[name*="part_number"], [name*="instruction_text"]');
            if (partInp) fillFieldset = partInp.closest('fieldset');
        }
        if (mcqFieldset === fillFieldset) mcqFieldset = fillFieldset = null;
        if (mcqFieldset) toggleFieldset(mcqFieldset, showMcqFields);
        if (fillFieldset) toggleFieldset(fillFieldset, showJsonFields);
        if (fillFieldset) fillFieldset.classList.toggle('question-type-fill-visible', showJsonFields);

        // 1) data-role orqali (forma maydonlarida qt-mcq / qt-fill qo'yilgan)
        container.querySelectorAll('[data-role="qt-mcq"]').forEach(function(inp) {
            var row = findRowForInput(inp);
            if (row) {
                row.style.display = showMcqFields ? '' : 'none';
                row.classList.toggle('question-type-row-hidden', !showMcqFields);
            }
        });
        container.querySelectorAll('[data-role="qt-fill"]').forEach(function(inp) {
            var row = findRowForInput(inp);
            if (row) {
                row.style.display = showJsonFields ? '' : 'none';
                row.classList.toggle('question-type-row-hidden', !showJsonFields);
            }
        });
        container.querySelectorAll('[data-role="qt-sa-rows"]').forEach(function(inp) {
            var row = findRowForInput(inp);
            if (row) {
                var showSa = showJsonFields && qType === 'short_answer';
                row.style.display = showSa ? '' : 'none';
                row.classList.toggle('question-type-row-hidden', !showSa);
            }
        });

        // 1.5) Granular show/hide (admin komfort uchun)
        function toggleByField(fieldKey, show) {
            container.querySelectorAll('[data-qt-field="' + fieldKey + '"]').forEach(function(inp) {
                var row = findRowForInput(inp);
                if (row) {
                    row.style.display = show ? '' : 'none';
                    row.classList.toggle('question-type-row-hidden', !show);
                }
            });
        }
        var isShort = qType === 'short_answer';
        var isEssay = qType === 'essay';
        var isFill = ['fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion'].indexOf(qType) >= 0;
        var isMatching = ['matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification'].indexOf(qType) >= 0;
        var isListSel = qType === 'list_selection';

        // Part raqami barcha JSON-ish bloklar uchun ko'rsatildi (baribir writing da task uchun kerak)
        var showPart = (isFill || isShort || isMatching || isListSel || isEssay);
        toggleByField('part_number', showPart);

        // Fill-in turlari: instruction + fill_answers
        toggleByField('instruction_text', isFill);
        toggleByField('fill_answers', isFill);
        toggleByField('writing_task_images', isEssay);

        // Matching turlari
        toggleByField('matching_items', isMatching);
        toggleByField('matching_options', isMatching);
        toggleByField('matching_correct', isMatching);

        // List selection
        toggleByField('list_options_simple', isListSel);
        toggleByField('list_correct_simple', isListSel);

        // 2) data-role bo'lmasa (eski sahifa) — name orqali zaxira
        if (container.querySelectorAll('[data-role="qt-mcq"]').length === 0) {
            var optionsBlock = findOptionsBlock(container);
            if (optionsBlock) {
                optionsBlock.style.display = showMcqFields ? '' : 'none';
                optionsBlock.classList.toggle('question-type-row-hidden', !showMcqFields);
            }
            container.querySelectorAll('input[name*="correct_answer"]').forEach(function(inp) {
                if ((inp.name || '').indexOf('correct_answer_json') === -1) toggleFormRow(inp, showMcqFields);
            });
        }
        if (container.querySelectorAll('[data-role="qt-fill"]').length === 0) {
            var fillNames = ['part_number', 'instruction_text', 'fill_answers', 'writing_task_images', 'matching_items', 'matching_options', 'matching_correct', 'list_options_simple', 'list_correct_simple'];
            fillNames.forEach(function(name) {
                container.querySelectorAll('[name*="' + name + '"]').forEach(function(inp) { toggleFormRow(inp, showJsonFields); });
            });
        }

        // 3) JSON (collapse blok)
        container.querySelectorAll('[name*="correct_answer_json"], [name*="options_json"]').forEach(function(inp) {
            var row = findRowForInput(inp);
            if (row) row.style.display = showJsonFields ? '' : 'none';
        });
    }

    function initQuestionForm(container) {
        if (!container) return;
        var typeSelect = container.querySelector('select[name*="question_type"]');
        if (typeSelect) {
            typeSelect.removeEventListener('change', typeSelect._qtHandler);
            typeSelect._qtHandler = function() { toggleByQuestionType(container); };
            typeSelect.addEventListener('change', typeSelect._qtHandler);
            toggleByQuestionType(container);
        }
    }

    function ensureStylePreview(container) {
        if (!container) return null;
        var existing = container.querySelector('.qt-style-preview');
        if (existing) return existing;

        var preview = document.createElement('div');
        preview.className = 'qt-style-preview';
        preview.innerHTML = (
            '<div class="qt-style-preview-title">UI Preview</div>' +
            '<div data-role="inst-preview" style="display:none;"></div>' +
            '<div data-role="prompt-preview"></div>'
        );

        var promptSelect = container.querySelector('select[name*="prompt_text_style"]');
        if (promptSelect) {
            var row = promptSelect.closest('.form-row') || promptSelect.parentElement;
            if (row && row.parentNode) row.parentNode.insertBefore(preview, row.nextSibling);
            else container.appendChild(preview);
        } else {
            container.appendChild(preview);
        }
        return preview;
    }

    function updateStylePreview(container) {
        if (!container) return;
        var preview = ensureStylePreview(container);
        if (!preview) return;

        var instSelect = container.querySelector('select[name*="instruction_box_style"]');
        var promptSelect = container.querySelector('select[name*="prompt_text_style"]');
        var instTextArea = container.querySelector('textarea[name*="instruction_text"]');
        var qTextArea = container.querySelector('textarea[name*="question_text"]');

        var instStyle = instSelect && instSelect.value ? instSelect.value : 'plain';
        var promptStyle = promptSelect && promptSelect.value ? promptSelect.value : 'default';
        var instText = instTextArea && instTextArea.value ? instTextArea.value.trim() : '';
        var qText = qTextArea && qTextArea.value ? qTextArea.value.trim() : '';

        var instEl = preview.querySelector('[data-role="inst-preview"]');
        var promptEl = preview.querySelector('[data-role="prompt-preview"]');
        if (!instEl || !promptEl) return;

        instEl.textContent = instText;
        instEl.className = 'admin-instruction-box admin-instruction-box--' + instStyle;
        instEl.style.display = instText ? '' : 'none';

        promptEl.textContent = qText || '(Savol matni kiritilmagan)';
        promptEl.className = 'admin-prompt-text';
        if (promptStyle && promptStyle !== 'default') {
            promptEl.classList.add('admin-prompt-text--' + promptStyle);
        }
    }

    function initStylePreview(container) {
        if (!container) return;
        if (container.dataset && container.dataset.qtStylePreviewInited === '1') {
            updateStylePreview(container);
            return;
        }
        if (container.dataset) container.dataset.qtStylePreviewInited = '1';
        var instSelect = container.querySelector('select[name*="instruction_box_style"]');
        var promptSelect = container.querySelector('select[name*="prompt_text_style"]');
        var instTextArea = container.querySelector('textarea[name*="instruction_text"]');
        var qTextArea = container.querySelector('textarea[name*="question_text"]');

        var update = function() { updateStylePreview(container); };
        if (instSelect) instSelect.addEventListener('change', update);
        if (promptSelect) promptSelect.addEventListener('change', update);
        if (instTextArea) {
            instTextArea.addEventListener('input', update);
            instTextArea.addEventListener('change', update);
        }
        if (qTextArea) {
            qTextArea.addEventListener('input', update);
            qTextArea.addEventListener('change', update);
        }
        updateStylePreview(container);
    }

    function init() {
        var mainForm = document.getElementById('question_form') || document.querySelector('#content-main form');
        if (mainForm) initQuestionForm(mainForm);
        if (mainForm) initStylePreview(mainForm);
        var inlines = document.querySelectorAll('.inline-related');
        inlines.forEach(function(el) {
            if (el.querySelector('select[name*="question_type"]')) initQuestionForm(el);
            initStylePreview(el);
        });
    }

    function runInit() {
        init();
        setTimeout(init, 100);
        setTimeout(init, 400);
        setTimeout(init, 800);
    }

    function getContainerForSelect(select) {
        if (!select) return null;
        return select.closest('.inline-related') || select.closest('form') || null;
    }

    function attachDelegation() {
        var body = document.body;
        if (!body) return;
        body.addEventListener('change', function(e) {
            if (e.target && e.target.matches && e.target.matches('select[name*="question_type"]')) {
                var container = getContainerForSelect(e.target);
                if (container) toggleByQuestionType(container);
            }
        }, true);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            attachDelegation();
            runInit();
        });
        window.addEventListener('load', runInit);
    } else {
        attachDelegation();
        runInit();
    }

    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).on('formset:added', function(e, $row, name) {
            if (String(name).indexOf('question') >= 0 && $row && $row[0]) {
                initQuestionForm($row[0]);
            }
        });
    }
    if (window.MutationObserver) {
        var initTimer;
        var obs = new MutationObserver(function() {
            if (initTimer) clearTimeout(initTimer);
            initTimer = setTimeout(function() { init(); initTimer = null; }, 200);
        });
        function observeWhenReady() {
            var target = document.querySelector('[id*="question"][id$="-group"]') || document.querySelector('#content-main') || document.body;
            if (target) obs.observe(target, { childList: true, subtree: true });
        }
        if (document.body) observeWhenReady(); else document.addEventListener('DOMContentLoaded', observeWhenReady);
    }
})();
