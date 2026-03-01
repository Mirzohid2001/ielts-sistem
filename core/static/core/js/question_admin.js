/**
 * Admin panel - Savol turi bo'yicha maydonlarni ko'rsatish/yashirish
 */
(function() {
    'use strict';

    var MCQ_TYPES = ['mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given'];
    var ONLY_AB = ['true_false'];           // faqat A va B (True/False)
    var ONLY_ABC = ['true_false_not_given', 'yes_no_not_given'];  // A, B, C — D kerak emas
    var FILL_TYPES = ['fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer'];
    var MATCHING_TYPES = ['matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification', 'list_selection'];

    function showMcq(qType) { return MCQ_TYPES.indexOf(qType) >= 0; }
    function showJson(qType) { return FILL_TYPES.indexOf(qType) >= 0 || MATCHING_TYPES.indexOf(qType) >= 0; }
    function showOptionC(qType) { return qType === 'mcq' || ONLY_ABC.indexOf(qType) >= 0; }  // True/False da C ham yashirin
    function showOptionD(qType) { return qType === 'mcq'; }  // D faqat MCQ da

    function toggleFieldset(fieldset, show) {
        if (!fieldset) return;
        var el = typeof fieldset === 'string' ? document.querySelector(fieldset) : fieldset;
        if (el) el.style.display = show ? 'block' : 'none';
    }

    function toggleFormRow(input, show) {
        if (!input) return;
        var row = input.closest('.form-row') || input.closest('div');
        if (row) row.style.display = show ? '' : 'none';
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

        // Asosiy form (fieldsets)
        var mcqFieldset = container.querySelector('.question-mcq-fields');
        var fillFieldset = container.querySelector('.question-fill-fields');
        toggleFieldset(mcqFieldset, showMcqFields);
        toggleFieldset(fillFieldset, showJsonFields);

        // Inline - field bo'yicha (True/False da faqat A,B; Yes/No/Not Given da A,B,C; MCQ da A,B,C,D)
        var showC = showMcqFields && showOptionC(qType);
        var showD = showMcqFields && showOptionD(qType);
        container.querySelectorAll('[name*="option_a"], [name*="option_b"]').forEach(function(inp) {
            toggleFormRow(inp, showMcqFields);
        });
        container.querySelectorAll('[name*="option_c"]').forEach(function(inp) {
            toggleOptionColumn(inp, showC);
        });
        container.querySelectorAll('[name*="option_d"]').forEach(function(inp) {
            toggleOptionColumn(inp, showD);
        });
        container.querySelectorAll('[name*="correct_answer"]').forEach(function(inp) {
            toggleFormRow(inp, showMcqFields);
        });
        var jsonFields = ['correct_answer_json', 'options_json'];
        var fillMatchingFields = ['part_number', 'instruction_text', 'fill_answers', 'matching_items', 'matching_options', 'matching_correct', 'list_options_simple', 'list_correct_simple'];
        jsonFields.forEach(function(name) {
            container.querySelectorAll('[name*="' + name + '"]').forEach(function(inp) {
                toggleFormRow(inp, showJsonFields);
            });
        });
        fillMatchingFields.forEach(function(name) {
            container.querySelectorAll('[name*="' + name + '"]').forEach(function(inp) {
                toggleFormRow(inp, showJsonFields);
            });
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

    function init() {
        initQuestionForm(document.getElementById('question_form') || document.querySelector('form'));
        document.querySelectorAll('.inline-related').forEach(initQuestionForm);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).on('formset:added', function(e, $row, name) {
            if (String(name).indexOf('question') >= 0) initQuestionForm($row[0]);
        });
    }
})();
