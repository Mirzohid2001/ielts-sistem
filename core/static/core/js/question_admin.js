/**
 * Admin panel - Savol turi bo'yicha maydonlarni ko'rsatish/yashirish
 */
(function() {
    'use strict';

    var MCQ_TYPES = ['mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given'];
    var FILL_TYPES = ['fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer'];
    var MATCHING_TYPES = ['matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification', 'list_selection'];

    function showMcq(qType) { return MCQ_TYPES.indexOf(qType) >= 0; }
    function showJson(qType) { return FILL_TYPES.indexOf(qType) >= 0 || MATCHING_TYPES.indexOf(qType) >= 0; }

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

    function toggleByQuestionType(container) {
        var select = container.querySelector('select[name*="question_type"]');
        if (!select) return;

        var qType = select.value;
        var showMcqFields = showMcq(qType);
        var showJsonFields = showJson(qType);

        // Asosiy form (fieldsets)
        var mcqFieldset = container.querySelector('.question-mcq-fields');
        var fillFieldset = container.querySelector('.question-fill-fields');
        toggleFieldset(mcqFieldset, showMcqFields);
        toggleFieldset(fillFieldset, showJsonFields);

        // Inline - field bo'yicha
        var mcqFields = ['option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'];
        var jsonFields = ['correct_answer_json', 'options_json'];
        mcqFields.forEach(function(name) {
            container.querySelectorAll('[name*="' + name + '"]').forEach(function(inp) {
                toggleFormRow(inp, showMcqFields);
            });
        });
        jsonFields.forEach(function(name) {
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
