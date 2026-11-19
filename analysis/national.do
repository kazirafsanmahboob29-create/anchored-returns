* National electric rate-case figures using the same validated tables as R/Python.
* Native execution requires a licensed Stata installation.
version 17.0
clear all
set more off
args study_dir
if "`study_dir'" == "" local study_dir "reports/national-study"
use "`study_dir'/annual.dta", clear
keep if year <= 2024
generate allowed_percent = mean_award_bp / 100
generate treasury_percent = mean_treasury_bp / 100
twoway line allowed_percent year, sort lcolor(navy) lwidth(medthick) ///
    title("Mean allowed electric ROE") ytitle("Percent") xtitle("Authorization year") ///
    graphregion(color(white)) name(longrun, replace)
graph export "`study_dir'/stata_annual.png", replace width(1600)
twoway (line allowed_percent year if year>=2010, sort lcolor(navy)) ///
    (line treasury_percent year if year>=2010, sort lcolor(gs9)), ///
    legend(order(1 "Allowed ROE" 2 "Treasury at authorization")) ///
    ytitle("Percent") xtitle("Authorization year") graphregion(color(white))
graph export "`study_dir'/stata_recent.png", replace width(1600)
* Regional means come from the same source-linked publisher observations.
import delimited "`study_dir'/regional_states.csv", clear varnames(1)
encode state, generate(state_id)
generate earlier_percent = earlier_mean_bp / 100
generate later_percent = later_mean_bp / 100
twoway (pcspike state_id earlier_percent state_id later_percent, lcolor(gs12)) ///
    (scatter state_id earlier_percent, msymbol(Oh) mcolor(gs9)) ///
    (scatter state_id later_percent, msymbol(O) mcolor(navy)), ///
    ylabel(, valuelabel angle(0)) ytitle("") xtitle("Mean reported allowed ROE (%)") ///
    legend(order(2 "2010-2014" 3 "2020-2024")) graphregion(color(white))
graph export "`study_dir'/stata_regional.png", replace width(1500)
