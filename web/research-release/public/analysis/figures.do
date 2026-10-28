* Anchored Returns | Kazi Rafsan Mahboob
* Native Stata graphs from the same validated tables used by R and Python.
* Execution has not been verified in Stata on this computer.
* do "analysis/figures.do" "INPUT_DIRECTORY" "OUTPUT_DIRECTORY"
version 14.2
clear all
set more off
args input output
if `"`input'"' == "" | `"`output'"' == "" {
    display as error "Supply the data directory and output directory."
    exit 198
}
capture mkdir `"`output'"'
log using `"`output'/stata_run.log"', text replace
set scheme s2color

use `"`input'/outcomes.dta"', clear
isid case_id
assert final_sample == 0
assert abs(gap_bp - (award_pct-request_pct)*100) < 1e-8 if !missing(request_pct,award_pct)
assert missing(gap_bp) if missing(request_pct) | missing(award_pct)
sort order_date case_id
generate row = _N - _n + 1
generate str80 case_label = state + " / " + docket
generate str40 gap_label = cond(missing(gap_bp),"Request missing", ///
    cond(gap_bp>0,"+","")+strtrim(string(gap_bp,"%5.0f"))+" bp")
generate label_x = 11.25
local ylabels
forvalues i=1/`=_N' {
    local y = row[`i']
    local label = case_label[`i']
    local ylabels `"`ylabels' `y' "`label'""'
}
twoway (rspike request_pct award_pct row, horizontal lcolor(gs11)) ///
    (scatter row request_pct, msymbol(Oh) mcolor("32 122 119") msize(medium)) ///
    (scatter row award_pct if award_kind=="commission_determined", msymbol(O) mcolor("208 149 80")) ///
    (scatter row award_pct if award_kind=="approved_settlement", msymbol(D) mcolor("104 125 153")) ///
    (scatter row label_x, msymbol(none) mlabel(gap_label) mlabposition(9) mlabcolor(gs6)), ///
    ylabel(`ylabels', angle(0) labsize(small) noticks) ytitle("") ///
    xtitle("Return on equity (%)") xlabel(8(.5)11.5) xscale(range(7.8 11.5)) ///
    title("Requested and allowed returns", position(11)) ///
    subtitle("Entered numeric records; the final 15-order sample remains pending", position(11)) ///
    legend(order(2 "Company request" 3 "Commission award" 4 "Approved settlement") rows(1) size(small)) ///
    note("Sources: original written orders; pages and URLs in outcomes.dta." ///
         "Original operative awards include recorded performance adjustments. Missing requests are not zero.", size(vsmall)) ///
    graphregion(color(white)) plotregion(color(white)) xsize(11) ysize(7) name(request_award, replace)
graph export `"`output'/request_award.pdf"', replace
graph export `"`output'/request_award.png"', width(2200) replace
preserve
keep if !missing(gap_bp)
keep case_id gap_bp
export delimited using `"`output'/checks.csv"', replace
restore

use `"`input'/coding.dta"', clear
isid case_id code
assert relied+considered+rejected+absent == denominator
assert abs(relied_pct+considered_pct+rejected_pct+absent_pct-100)<1e-8
label variable relied_pct "Relied on"
label variable considered_pct "Considered"
label variable rejected_pct "Rejected"
label variable absent_pct "Not present"
generate str24 unit_label = state + " (n=" + string(denominator,"%2.0f") + ")"
graph hbar (asis) relied_pct considered_pct rejected_pct absent_pct, ///
    over(unit_label, label(labsize(small))) by(code, cols(3) ///
    title("Evidence categories and stance") ///
    note("First-pass Commission-analysis units. Codes can overlap; independent agreement is unmeasured.", size(vsmall))) ///
    stack bar(1,color("32 122 119")) bar(2,color("169 198 194")) ///
    bar(3,color("190 121 89")) bar(4,color("238 241 240")) ///
    ylabel(0(25)100) ytitle("Share of units (%)") ///
    legend(rows(1) size(vsmall)) graphregion(color(white)) xsize(11) ysize(7) name(evidence_stances, replace)
graph export `"`output'/evidence_stances.pdf"', replace
graph export `"`output'/evidence_stances.png"', width(2200) replace

use `"`input'/benchmarks.dta"', clear
isid service period_start period_end
assert riders_excluded==1
assert dataset_version=="legacy_major_rate_case_coverage"
twoway (scatter mean_pct period_end if service=="Electric", mcolor("32 122 119") msymbol(O)) ///
       (scatter mean_pct period_end if service=="Gas", mcolor("208 149 80") msymbol(T)), ///
       title("Verified national comparison points",position(11)) ///
       xtitle("Covered half-year end") ytitle("Mean authorized ROE (%)") ///
       legend(order(1 "Electric" 2 "Gas") rows(1)) graphregion(color(white)) ///
       note("Sources: original RRA reports in commission filings. General rate cases excluding riders." ///
            "H2 2019 is reconstructed from complete case rows; other means are publisher reported. Missing periods are not interpolated.",size(vsmall)) ///
       name(verified_benchmarks,replace)
graph export `"`output'/verified_benchmarks.pdf"', replace
graph export `"`output'/verified_benchmarks.png"', width(2100) replace
log close
