// HDO - Humboldt Digital Ocean
// JavaScript utilities

document.addEventListener("DOMContentLoaded", function() {
    // Helper: formato de fecha
    window.hdoFormatDate = function(dateStr) {
        if (!dateStr) return "N/D";
        var d = new Date(dateStr + "T00:00:00");
        return d.toLocaleDateString("es-CL", { year: "numeric", month: "short", day: "numeric" });
    };

    // Helper: formato número
    window.hdoFormatNum = function(val, decimals) {
        if (val === null || val === undefined) return "N/D";
        decimals = decimals || 2;
        return Number(val).toFixed(decimals);
    };
});