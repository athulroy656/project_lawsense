// TEMP FILE - Boolean guard functions for financial sections

// Rule A: Term & Validity - show if duration OR expiration exists
const showTermValidity = (financialData) => {
    if (!financialData) return false;
    return financialData.duration?.found || financialData.expiration?.found;
};

// Rule B: Financial Exposure - show if liability cap OR meaningful penalties exist
const showFinancialExposure = (financialData) => {
    if (!financialData) return false;

    const hasLiabilityCap = financialData.liability_cap?.found;
    const hasPenalties = Array.isArray(financialData.penalties) &&
        financialData.penalties.some(p => {
            const amt = formatAmount(p.amount);
            return amt && amt !== "—" && amt !== "Not specified" && (p.source || p.source_text);
        });

    return hasLiabilityCap || hasPenalties;
};

// Rule C: Deadlines - show if deadlines array has items
const showDeadlines = (financialData) => {
    if (!financialData) return false;
    return Array.isArray(financialData.deadlines) && financialData.deadlines.length > 0;
};
