import{i as e,m as t,p as n,s as r}from"./lit-runtime-gkTRPNbC.js";import{o as i}from"./string-coerce-DwnRzrPh.js";import{F as a,I as o,V as s,W as c,_ as l,a as u,gt as d,mt as f,n as p,ut as m}from"./index-DRTyMBOr.js";function h(){return[{value:`ok`,label:i(`cron.runs.runStatusOk`)},{value:`error`,label:i(`cron.runs.runStatusError`)},{value:`skipped`,label:i(`cron.runs.runStatusSkipped`)}]}function g(){return[{value:`delivered`,label:i(`cron.runs.deliveryDelivered`)},{value:`not-delivered`,label:i(`cron.runs.deliveryNotDelivered`)},{value:`unknown`,label:i(`cron.runs.deliveryUnknown`)},{value:`not-requested`,label:i(`cron.runs.deliveryNotRequested`)}]}function _(e,t,n){let r=new Set(e);return n?r.add(t):r.delete(t),Array.from(r)}function v(e,t){return e.length===0?t:e.length<=2?e.join(`, `):`${e[0]} +${e.length-1}`}function y(e){let t=[`last`,...e.channels.filter(Boolean)],n=e.form.deliveryChannel?.trim();n&&!t.includes(n)&&t.push(n);let r=new Set;return t.filter(e=>r.has(e)?!1:(r.add(e),!0))}function b(e,t){if(t===`last`)return`last`;let n=e.channelMeta?.find(e=>e.id===t);return n?.label?n.label:e.channelLabels?.[t]??t}function x(e){return t`
    <div class="field cron-filter-dropdown" data-filter=${e.id}>
      <span>${e.title}</span>
      <details class="cron-filter-dropdown__details">
        <summary class="btn cron-filter-dropdown__trigger">
          <span>${e.summary}</span>
        </summary>
        <div class="cron-filter-dropdown__panel">
          <div class="cron-filter-dropdown__list">
            ${e.options.map(n=>t`
                <label class="cron-filter-dropdown__option">
                  <input
                    type="checkbox"
                    value=${n.value}
                    .checked=${e.selected.includes(n.value)}
                    @change=${t=>{let r=t.target;e.onToggle(n.value,r.checked)}}
                  />
                  <span>${n.label}</span>
                </label>
              `)}
          </div>
          <div class="row">
            <button class="btn" type="button" @click=${e.onClear}>
              ${i(`cron.runs.clear`)}
            </button>
          </div>
        </div>
      </details>
    </div>
  `}function S(e,r){let i=d(f(r));return i.length===0?n:t`<datalist id=${e}>
    ${i.map(e=>t`<option value=${e}></option> `)}
  </datalist>`}function C(e){return`cron-error-${e}`}function w(e){return e===`name`?`cron-name`:e===`scheduleAt`?`cron-schedule-at`:e===`everyAmount`?`cron-every-amount`:e===`cronExpr`?`cron-cron-expr`:e===`staggerAmount`?`cron-stagger-amount`:e===`payloadText`?`cron-payload-text`:e===`payloadModel`?`cron-payload-model`:e===`payloadThinking`?`cron-payload-thinking`:e===`timeoutSeconds`?`cron-timeout-seconds`:e===`failureAlertAfter`?`cron-failure-alert-after`:e===`failureAlertCooldownSeconds`?`cron-failure-alert-cooldown-seconds`:`cron-delivery-to`}function T(e,t,n){return e===`payloadText`?t.payloadKind===`systemEvent`?i(`cron.form.mainTimelineMessage`):i(`cron.form.assistantTaskPrompt`):e===`deliveryTo`?i(n===`webhook`?`cron.form.webhookUrl`:`cron.form.to`):{name:i(`cron.form.fieldName`),scheduleAt:i(`cron.form.runAt`),everyAmount:i(`cron.form.every`),cronExpr:i(`cron.form.expression`),staggerAmount:i(`cron.form.staggerWindow`),payloadText:i(`cron.form.assistantTaskPrompt`),payloadModel:i(`cron.form.model`),payloadThinking:i(`cron.form.thinking`),timeoutSeconds:i(`cron.form.timeoutSeconds`),deliveryTo:i(`cron.form.to`),failureAlertAfter:`Failure alert after`,failureAlertCooldownSeconds:`Failure alert cooldown`}[e]}function E(e,t,n){let r=[`name`,`scheduleAt`,`everyAmount`,`cronExpr`,`staggerAmount`,`payloadText`,`payloadModel`,`payloadThinking`,`timeoutSeconds`,`deliveryTo`,`failureAlertAfter`,`failureAlertCooldownSeconds`],i=[];for(let a of r){let r=e[a];r&&i.push({key:a,label:T(a,t,n),message:r,inputId:w(a)})}return i}function D(e){let t=document.getElementById(e);t instanceof HTMLElement&&(typeof t.scrollIntoView==`function`&&t.scrollIntoView({block:`center`,behavior:`smooth`}),t.focus())}function O(e,r=!1){return t`<span>
    ${e}
    ${r?t`
          <span class="cron-required-marker" aria-hidden="true">*</span>
          <span class="cron-required-sr">${i(`cron.form.requiredSr`)}</span>
        `:n}
  </span>`}function k(e){let a=!!e.editingJobId,o=e.form.payloadKind===`agentTurn`,s=e.form.scheduleKind===`cron`,c=y(e),l=e.runsJobId==null?void 0:e.jobs.find(t=>t.id===e.runsJobId),d=e.runsScope===`all`?i(`cron.jobList.allJobs`):l?.name??e.runsJobId??i(`cron.jobList.selectJob`),f=e.runs.toSorted((t,n)=>e.runsSortDir===`asc`?t.ts-n.ts:n.ts-t.ts),p=h(),m=g(),w=p.filter(t=>e.runsStatuses.includes(t.value)).map(e=>e.label),T=m.filter(t=>e.runsDeliveryStatuses.includes(t.value)).map(e=>e.label),k=v(w,i(`cron.runs.allStatuses`)),N=v(T,i(`cron.runs.allDelivery`)),P=e.form.sessionTarget!==`main`&&e.form.payloadKind===`agentTurn`,F=e.form.deliveryMode===`announce`&&!P?`none`:e.form.deliveryMode,I=e.cronFormCollapsed===!1||a,L=!I,R=i(a?`cron.form.editJob`:`cron.form.newJob`),z=E(e.fieldErrors,e.form,F),V=!e.busy&&z.length>0,H=e.onQuickCreate?e.onQuickCreate:e.onToggleFormCollapsed?()=>e.onToggleFormCollapsed?.(!1):null,U=e.jobsQuery.trim().length>0||e.jobsEnabledFilter!==`all`||e.jobsScheduleKindFilter!==`all`||e.jobsLastStatusFilter!==`all`||e.jobsSortBy!==`nextRunAtMs`||e.jobsSortDir!==`asc`,W=e.runsScope!==`all`||e.runsQuery.trim().length>0||e.runsStatuses.length>0||e.runsDeliveryStatuses.length>0||e.runsSortDir!==`desc`,G=V&&!e.canSubmit?z.length===1?i(`cron.form.fixFields`,{count:String(z.length)}):i(`cron.form.fixFieldsPlural`,{count:String(z.length)}):``;return t`
    <section class="card cron-summary-strip">
      <div class="cron-summary-strip__left">
        <div class="cron-summary-item">
          <div class="cron-summary-label">${i(`cron.summary.enabled`)}</div>
          <div class="cron-summary-value">
            <span class=${`chip ${e.status?.enabled?`chip-ok`:`chip-danger`}`}>
              ${e.status?e.status.enabled?i(`cron.summary.yes`):i(`cron.summary.no`):i(`common.na`)}
            </span>
          </div>
        </div>
        <div class="cron-summary-item">
          <div class="cron-summary-label">${i(`cron.summary.jobs`)}</div>
          <div class="cron-summary-value">${e.status?.jobs??i(`common.na`)}</div>
        </div>
        <div class="cron-summary-item cron-summary-item--wide">
          <div class="cron-summary-label">${i(`cron.summary.nextWake`)}</div>
          <div class="cron-summary-value">${u(e.status?.nextWakeAtMs??null)}</div>
        </div>
      </div>
      <div class="cron-summary-strip__actions">
        ${H?t`
              <button class="btn btn--primary" @click=${H}>
                ${i(`cron.form.newJob`)}
              </button>
            `:n}
        <button
          class=${e.loading?`btn cron-refresh-btn--loading`:`btn`}
          ?disabled=${e.loading}
          @click=${e.onRefresh}
        >
          ${e.loading?i(`cron.summary.refreshing`):i(`cron.summary.refresh`)}
        </button>
        ${e.error?t`<span class="muted">${e.error}</span>`:n}
      </div>
    </section>

    <section class=${`cron-workspace ${L?`cron-workspace--form-collapsed`:``}`}>
      <div class="cron-workspace-main">
        <section class="card">
          <div
            class="row"
            style="justify-content: space-between; align-items: flex-start; gap: 12px;"
          >
            <div>
              <div class="card-title">${i(`cron.jobs.title`)}</div>
              <div class="card-sub">${i(`cron.jobs.subtitle`)}</div>
            </div>
            <div class="muted">
              ${i(`cron.jobs.shownOf`,{shown:String(e.jobs.length),total:String(e.jobsTotal)})}
            </div>
          </div>
          <details class="cron-filter-panel" ?open=${U}>
            <summary class="cron-filter-panel__summary">
              <span>${i(`sessionsView.filters`)}</span>
              ${U?t`<span class="chip">${i(`common.active`)}</span>`:n}
            </summary>
            <div class="filters cron-filter-panel__body">
              <label class="field cron-filter-search">
                <span>${i(`cron.jobs.searchJobs`)}</span>
                <input
                  .value=${e.jobsQuery}
                  placeholder=${i(`cron.jobs.searchPlaceholder`)}
                  @input=${t=>e.onJobsFiltersChange({cronJobsQuery:t.target.value})}
                />
              </label>
              <label class="field">
                <span>${i(`cron.jobs.enabled`)}</span>
                <select
                  .value=${e.jobsEnabledFilter}
                  @change=${t=>e.onJobsFiltersChange({cronJobsEnabledFilter:t.target.value})}
                >
                  <option value="all">${i(`cron.jobs.all`)}</option>
                  <option value="enabled">${i(`common.enabled`)}</option>
                  <option value="disabled">${i(`common.disabled`)}</option>
                </select>
              </label>
              <label class="field">
                <span>${i(`cron.jobs.schedule`)}</span>
                <select
                  data-test-id="cron-jobs-schedule-filter"
                  .value=${e.jobsScheduleKindFilter}
                  @change=${t=>e.onJobsFiltersChange({cronJobsScheduleKindFilter:t.target.value})}
                >
                  <option value="all">${i(`cron.jobs.all`)}</option>
                  <option value="at">${i(`cron.form.at`)}</option>
                  <option value="every">${i(`cron.form.every`)}</option>
                  <option value="cron">${i(`cron.form.cronOption`)}</option>
                </select>
              </label>
              <label class="field">
                <span>${i(`cron.jobs.lastRun`)}</span>
                <select
                  data-test-id="cron-jobs-last-status-filter"
                  .value=${e.jobsLastStatusFilter}
                  @change=${t=>e.onJobsFiltersChange({cronJobsLastStatusFilter:t.target.value})}
                >
                  <option value="all">${i(`cron.jobs.all`)}</option>
                  <option value="ok">${i(`cron.runs.runStatusOk`)}</option>
                  <option value="error">${i(`cron.runs.runStatusError`)}</option>
                  <option value="skipped">${i(`cron.runs.runStatusSkipped`)}</option>
                  <option value="unknown">${i(`cron.runs.runStatusUnknown`)}</option>
                </select>
              </label>
              <label class="field">
                <span>${i(`cron.jobs.sort`)}</span>
                <select
                  .value=${e.jobsSortBy}
                  @change=${t=>e.onJobsFiltersChange({cronJobsSortBy:t.target.value})}
                >
                  <option value="nextRunAtMs">${i(`cron.jobs.nextRun`)}</option>
                  <option value="updatedAtMs">${i(`cron.jobs.recentlyUpdated`)}</option>
                  <option value="name">${i(`cron.jobs.name`)}</option>
                </select>
              </label>
              <label class="field">
                <span>${i(`cron.jobs.direction`)}</span>
                <select
                  .value=${e.jobsSortDir}
                  @change=${t=>e.onJobsFiltersChange({cronJobsSortDir:t.target.value})}
                >
                  <option value="asc">${i(`cron.jobs.ascending`)}</option>
                  <option value="desc">${i(`cron.jobs.descending`)}</option>
                </select>
              </label>
              <label class="field">
                <span>${i(`cron.jobs.reset`)}</span>
                <button
                  class="btn"
                  data-test-id="cron-jobs-filters-reset"
                  ?disabled=${!U}
                  @click=${e.onJobsFiltersReset}
                >
                  ${i(`cron.jobs.reset`)}
                </button>
              </label>
            </div>
          </details>
          ${e.jobs.length===0?t`
                <div class="cron-empty-state">
                  <div class="cron-empty-state__title">
                    ${i(U?`cron.jobs.noMatching`:`cron.jobs.emptyTitle`)}
                  </div>
                  <div class="cron-empty-state__copy">
                    ${i(U?`cron.jobs.emptyFilteredHint`:`cron.jobs.emptyHint`)}
                  </div>
                  ${H&&!U?t`
                        <button class="btn btn--primary" @click=${H}>
                          ${i(`cron.form.newJob`)}
                        </button>
                      `:n}
                </div>
              `:t`
                <div class="list" style="margin-top: 12px;">
                  ${e.jobs.map(t=>M(t,e))}
                </div>
              `}
          ${e.jobsHasMore?t`
                <div class="row" style="margin-top: 12px">
                  <button
                    class="btn"
                    ?disabled=${e.loading||e.jobsLoadingMore}
                    @click=${e.onLoadMoreJobs}
                  >
                    ${e.jobsLoadingMore?i(`cron.jobs.loading`):i(`cron.jobs.loadMore`)}
                  </button>
                </div>
              `:n}
        </section>

        <section class="card">
          <div
            class="row"
            style="justify-content: space-between; align-items: flex-start; gap: 12px;"
          >
            <div>
              <div class="card-title">${i(`cron.runs.title`)}</div>
              <div class="card-sub">
                ${e.runsScope===`all`?i(`cron.runs.subtitleAll`):i(`cron.runs.subtitleJob`,{title:d})}
              </div>
            </div>
            <div class="muted">
              ${i(`cron.jobs.shownOf`,{shown:String(f.length),total:String(e.runsTotal)})}
            </div>
          </div>
          <details class="cron-filter-panel" ?open=${W}>
            <summary class="cron-filter-panel__summary">
              <span>${i(`sessionsView.filters`)}</span>
              ${W?t`<span class="chip">${i(`common.active`)}</span>`:n}
            </summary>
            <div class="cron-run-filters">
              <div class="cron-run-filters__row cron-run-filters__row--primary">
                <label class="field">
                  <span>${i(`cron.runs.scope`)}</span>
                  <select
                    .value=${e.runsScope}
                    @change=${t=>e.onRunsFiltersChange({cronRunsScope:t.target.value})}
                  >
                    <option value="all">${i(`cron.runs.allJobs`)}</option>
                    <option value="job" ?disabled=${e.runsJobId==null}>
                      ${i(`cron.runs.selectedJob`)}
                    </option>
                  </select>
                </label>
                <label class="field cron-run-filter-search">
                  <span>${i(`cron.runs.searchRuns`)}</span>
                  <input
                    .value=${e.runsQuery}
                    placeholder=${i(`cron.runs.searchPlaceholder`)}
                    @input=${t=>e.onRunsFiltersChange({cronRunsQuery:t.target.value})}
                  />
                </label>
                <label class="field">
                  <span>${i(`cron.jobs.sort`)}</span>
                  <select
                    .value=${e.runsSortDir}
                    @change=${t=>e.onRunsFiltersChange({cronRunsSortDir:t.target.value})}
                  >
                    <option value="desc">${i(`cron.runs.newestFirst`)}</option>
                    <option value="asc">${i(`cron.runs.oldestFirst`)}</option>
                  </select>
                </label>
              </div>
              <div class="cron-run-filters__row cron-run-filters__row--secondary">
                ${x({id:`status`,title:i(`cron.runs.status`),summary:k,options:p,selected:e.runsStatuses,onToggle:(t,n)=>{let r=_(e.runsStatuses,t,n);e.onRunsFiltersChange({cronRunsStatuses:r})},onClear:()=>{e.onRunsFiltersChange({cronRunsStatuses:[]})}})}
                ${x({id:`delivery`,title:i(`cron.runs.delivery`),summary:N,options:m,selected:e.runsDeliveryStatuses,onToggle:(t,n)=>{let r=_(e.runsDeliveryStatuses,t,n);e.onRunsFiltersChange({cronRunsDeliveryStatuses:r})},onClear:()=>{e.onRunsFiltersChange({cronRunsDeliveryStatuses:[]})}})}
              </div>
            </div>
          </details>
          ${e.runsScope===`job`&&e.runsJobId==null?t`
                <div class="muted" style="margin-top: 12px">${i(`cron.runs.selectJobHint`)}</div>
              `:f.length===0?t`
                  <div class="muted" style="margin-top: 12px">${i(`cron.runs.noMatching`)}</div>
                `:t`
                  <div class="list" style="margin-top: 12px;">
                    ${f.map(t=>B(t,e.basePath,e.onNavigateToChat))}
                  </div>
                `}
          ${(e.runsScope===`all`||e.runsJobId!=null)&&e.runsHasMore?t`
                <div class="row" style="margin-top: 12px">
                  <button
                    class="btn"
                    ?disabled=${e.runsLoadingMore}
                    @click=${e.onLoadMoreRuns}
                  >
                    ${e.runsLoadingMore?i(`cron.jobs.loading`):i(`cron.runs.loadMore`)}
                  </button>
                </div>
              `:n}
        </section>
      </div>
    </section>

    ${I?t`
          <div class="cron-form-modal-backdrop" @click=${e.onCancelEdit}>
            <section
              class="card cron-workspace-form cron-form-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="cron-form-title"
              @click=${e=>e.stopPropagation()}
            >
              <div class="cron-form-header">
                <div class="cron-form-header__copy">
                  <div id="cron-form-title" class="card-title">${R}</div>
                  ${L?n:t`
                        <div class="card-sub">
                          ${i(a?`cron.form.updateSubtitle`:`cron.form.createSubtitle`)}
                        </div>
                      `}
                </div>
                <button
                  type="button"
                  class="btn cron-form-collapse-toggle"
                  data-test-id="cron-form-close"
                  title=${i(`common.dismiss`)}
                  aria-label=${i(`common.dismiss`)}
                  @click=${e.onCancelEdit}
                >
                  <span aria-hidden="true">×</span>
                </button>
              </div>
              <div class="cron-form" ?hidden=${L}>
                <div class="cron-required-legend">
                  <span class="cron-required-marker" aria-hidden="true">*</span> ${i(`cron.form.required`)}
                </div>
                <section class="cron-form-section">
                  <div class="cron-form-section__title">${i(`cron.form.basics`)}</div>
                  <div class="cron-form-section__sub">${i(`cron.form.basicsSub`)}</div>
                  <div class="form-grid cron-form-grid">
                    <label class="field">
                      ${O(i(`cron.form.fieldName`),!0)}
                      <input
                        id="cron-name"
                        .value=${e.form.name}
                        placeholder=${i(`cron.form.namePlaceholder`)}
                        aria-invalid=${e.fieldErrors.name?`true`:`false`}
                        aria-describedby=${r(e.fieldErrors.name?C(`name`):void 0)}
                        @input=${t=>e.onFormChange({name:t.target.value})}
                      />
                      ${j(e.fieldErrors.name,C(`name`))}
                    </label>
                    <label class="field">
                      <span>${i(`cron.form.description`)}</span>
                      <input
                        .value=${e.form.description}
                        placeholder=${i(`cron.form.descriptionPlaceholder`)}
                        @input=${t=>e.onFormChange({description:t.target.value})}
                      />
                    </label>
                    <label class="field">
                      ${O(i(`cron.form.agentId`))}
                      <input
                        id="cron-agent-id"
                        .value=${e.form.agentId}
                        list="cron-agent-suggestions"
                        ?disabled=${e.form.clearAgent}
                        @input=${t=>e.onFormChange({agentId:t.target.value})}
                        placeholder=${i(`cron.form.agentPlaceholder`)}
                      />
                      <div class="cron-help">${i(`cron.form.agentHelp`)}</div>
                    </label>
                    <label class="field checkbox cron-checkbox cron-checkbox-inline">
                      <input
                        type="checkbox"
                        .checked=${e.form.enabled}
                        @change=${t=>e.onFormChange({enabled:t.target.checked})}
                      />
                      <span class="field-checkbox__label">${i(`cron.summary.enabled`)}</span>
                    </label>
                  </div>
                </section>

                <section class="cron-form-section">
                  <div class="cron-form-section__title">${i(`cron.form.schedule`)}</div>
                  <div class="cron-form-section__sub">${i(`cron.form.scheduleSub`)}</div>
                  <div class="form-grid cron-form-grid">
                    <label class="field cron-span-2">
                      ${O(i(`cron.form.schedule`))}
                      <select
                        id="cron-schedule-kind"
                        .value=${e.form.scheduleKind}
                        @change=${t=>e.onFormChange({scheduleKind:t.target.value})}
                      >
                        <option value="every">${i(`cron.form.every`)}</option>
                        <option value="at">${i(`cron.form.at`)}</option>
                        <option value="cron">${i(`cron.form.cronOption`)}</option>
                      </select>
                    </label>
                  </div>
                  ${A(e)}
                </section>

                <section class="cron-form-section">
                  <div class="cron-form-section__title">${i(`cron.form.execution`)}</div>
                  <div class="cron-form-section__sub">${i(`cron.form.executionSub`)}</div>
                  <div class="form-grid cron-form-grid">
                    <label class="field">
                      ${O(i(`cron.form.session`))}
                      <select
                        id="cron-session-target"
                        .value=${e.form.sessionTarget}
                        @change=${t=>e.onFormChange({sessionTarget:t.target.value})}
                      >
                        <option value="main">${i(`cron.form.main`)}</option>
                        <option value="isolated">${i(`cron.form.isolated`)}</option>
                      </select>
                      <div class="cron-help">${i(`cron.form.sessionHelp`)}</div>
                    </label>
                    <label class="field">
                      ${O(i(`cron.form.wakeMode`))}
                      <select
                        id="cron-wake-mode"
                        .value=${e.form.wakeMode}
                        @change=${t=>e.onFormChange({wakeMode:t.target.value})}
                      >
                        <option value="now">${i(`cron.form.now`)}</option>
                        <option value="next-heartbeat">${i(`cron.form.nextHeartbeat`)}</option>
                      </select>
                      <div class="cron-help">${i(`cron.form.wakeModeHelp`)}</div>
                    </label>
                    <label class="field ${o?``:`cron-span-2`}">
                      ${O(i(`cron.form.payloadKind`))}
                      <select
                        id="cron-payload-kind"
                        .value=${e.form.payloadKind}
                        @change=${t=>e.onFormChange({payloadKind:t.target.value})}
                      >
                        <option value="systemEvent">${i(`cron.form.systemEvent`)}</option>
                        <option value="agentTurn">${i(`cron.form.agentTurn`)}</option>
                      </select>
                      <div class="cron-help">
                        ${e.form.payloadKind===`systemEvent`?i(`cron.form.systemEventHelp`):i(`cron.form.agentTurnHelp`)}
                      </div>
                    </label>
                    ${o?t`
                          <label class="field">
                            ${O(i(`cron.form.timeoutSeconds`))}
                            <input
                              id="cron-timeout-seconds"
                              .value=${e.form.timeoutSeconds}
                              placeholder=${i(`cron.form.timeoutPlaceholder`)}
                              aria-invalid=${e.fieldErrors.timeoutSeconds?`true`:`false`}
                              aria-describedby=${r(e.fieldErrors.timeoutSeconds?C(`timeoutSeconds`):void 0)}
                              @input=${t=>e.onFormChange({timeoutSeconds:t.target.value})}
                            />
                            <div class="cron-help">${i(`cron.form.timeoutHelp`)}</div>
                            ${j(e.fieldErrors.timeoutSeconds,C(`timeoutSeconds`))}
                          </label>
                        `:n}
                  </div>
                  <label class="field cron-span-2">
                    ${O(e.form.payloadKind===`systemEvent`?i(`cron.form.mainTimelineMessage`):i(`cron.form.assistantTaskPrompt`),!0)}
                    <textarea
                      id="cron-payload-text"
                      .value=${e.form.payloadText}
                      aria-invalid=${e.fieldErrors.payloadText?`true`:`false`}
                      aria-describedby=${r(e.fieldErrors.payloadText?C(`payloadText`):void 0)}
                      @input=${t=>e.onFormChange({payloadText:t.target.value})}
                      rows="4"
                    ></textarea>
                    ${j(e.fieldErrors.payloadText,C(`payloadText`))}
                  </label>
                </section>

                <section class="cron-form-section">
                  <div class="cron-form-section__title">${i(`cron.form.deliverySection`)}</div>
                  <div class="cron-form-section__sub">${i(`cron.form.deliverySub`)}</div>
                  <div class="form-grid cron-form-grid">
                    <label class="field ${F===`none`?`cron-span-2`:``}">
                      ${O(i(`cron.form.resultDelivery`))}
                      <select
                        id="cron-delivery-mode"
                        .value=${F}
                        @change=${t=>e.onFormChange({deliveryMode:t.target.value})}
                      >
                        ${P?t`
                              <option value="announce">${i(`cron.form.announceDefault`)}</option>
                            `:n}
                        <option value="webhook">${i(`cron.form.webhookPost`)}</option>
                        <option value="none">${i(`cron.form.noneInternal`)}</option>
                      </select>
                      <div class="cron-help">${i(`cron.form.deliveryHelp`)}</div>
                    </label>
                    ${F===`none`?n:t`
                          <label
                            class="field ${F===`webhook`?`cron-span-2`:``}"
                          >
                            ${O(i(F===`webhook`?`cron.form.webhookUrl`:`cron.form.channel`),F===`webhook`)}
                            ${F===`webhook`?t`
                                  <input
                                    id="cron-delivery-to"
                                    .value=${e.form.deliveryTo}
                                    list="cron-delivery-to-suggestions"
                                    aria-invalid=${e.fieldErrors.deliveryTo?`true`:`false`}
                                    aria-describedby=${r(e.fieldErrors.deliveryTo?C(`deliveryTo`):void 0)}
                                    @input=${t=>e.onFormChange({deliveryTo:t.target.value})}
                                    placeholder=${i(`cron.form.webhookPlaceholder`)}
                                  />
                                `:t`
                                  <select
                                    id="cron-delivery-channel"
                                    .value=${e.form.deliveryChannel||`last`}
                                    @change=${t=>e.onFormChange({deliveryChannel:t.target.value})}
                                  >
                                    ${c.map(n=>t`<option value=${n}>
                                          ${b(e,n)}
                                        </option>`)}
                                  </select>
                                `}
                            ${F===`announce`?t` <div class="cron-help">${i(`cron.form.channelHelp`)}</div> `:t` <div class="cron-help">${i(`cron.form.webhookHelp`)}</div> `}
                          </label>
                          ${F===`announce`?t`
                                <label class="field cron-span-2">
                                  ${O(i(`cron.form.to`))}
                                  <input
                                    id="cron-delivery-to"
                                    .value=${e.form.deliveryTo}
                                    list="cron-delivery-to-suggestions"
                                    @input=${t=>e.onFormChange({deliveryTo:t.target.value})}
                                    placeholder=${i(`cron.form.toPlaceholder`)}
                                  />
                                  <div class="cron-help">${i(`cron.form.toHelp`)}</div>
                                </label>
                              `:n}
                          ${F===`webhook`?j(e.fieldErrors.deliveryTo,C(`deliveryTo`)):n}
                        `}
                  </div>
                </section>

                <details class="cron-advanced">
                  <summary class="cron-advanced__summary">${i(`cron.form.advanced`)}</summary>
                  <div class="cron-help">${i(`cron.form.advancedHelp`)}</div>
                  <div class="form-grid cron-form-grid">
                    <label class="field checkbox cron-checkbox">
                      <input
                        type="checkbox"
                        .checked=${e.form.deleteAfterRun}
                        @change=${t=>e.onFormChange({deleteAfterRun:t.target.checked})}
                      />
                      <span class="field-checkbox__label">${i(`cron.form.deleteAfterRun`)}</span>
                      <div class="cron-help">${i(`cron.form.deleteAfterRunHelp`)}</div>
                    </label>
                    <label class="field checkbox cron-checkbox">
                      <input
                        type="checkbox"
                        .checked=${e.form.clearAgent}
                        @change=${t=>e.onFormChange({clearAgent:t.target.checked})}
                      />
                      <span class="field-checkbox__label"
                        >${i(`cron.form.clearAgentOverride`)}</span
                      >
                      <div class="cron-help">${i(`cron.form.clearAgentHelp`)}</div>
                    </label>
                    <label class="field cron-span-2">
                      ${O(`Session key`)}
                      <input
                        id="cron-session-key"
                        .value=${e.form.sessionKey}
                        @input=${t=>e.onFormChange({sessionKey:t.target.value})}
                        placeholder="agent:main:main"
                      />
                      <div class="cron-help">
                        Optional routing key for job delivery and wake routing.
                      </div>
                    </label>
                    ${s?t`
                          <label class="field checkbox cron-checkbox cron-span-2">
                            <input
                              type="checkbox"
                              .checked=${e.form.scheduleExact}
                              @change=${t=>e.onFormChange({scheduleExact:t.target.checked})}
                            />
                            <span class="field-checkbox__label">${i(`cron.form.exactTiming`)}</span>
                            <div class="cron-help">${i(`cron.form.exactTimingHelp`)}</div>
                          </label>
                          <div class="cron-stagger-group cron-span-2">
                            <label class="field">
                              ${O(i(`cron.form.staggerWindow`))}
                              <input
                                id="cron-stagger-amount"
                                .value=${e.form.staggerAmount}
                                ?disabled=${e.form.scheduleExact}
                                aria-invalid=${e.fieldErrors.staggerAmount?`true`:`false`}
                                aria-describedby=${r(e.fieldErrors.staggerAmount?C(`staggerAmount`):void 0)}
                                @input=${t=>e.onFormChange({staggerAmount:t.target.value})}
                                placeholder=${i(`cron.form.staggerPlaceholder`)}
                              />
                              ${j(e.fieldErrors.staggerAmount,C(`staggerAmount`))}
                            </label>
                            <label class="field">
                              <span>${i(`cron.form.staggerUnit`)}</span>
                              <select
                                .value=${e.form.staggerUnit}
                                ?disabled=${e.form.scheduleExact}
                                @change=${t=>e.onFormChange({staggerUnit:t.target.value})}
                              >
                                <option value="seconds">${i(`cron.form.seconds`)}</option>
                                <option value="minutes">${i(`cron.form.minutes`)}</option>
                              </select>
                            </label>
                          </div>
                        `:n}
                    ${o?t`
                          <label class="field cron-span-2">
                            ${O(`Account ID`)}
                            <input
                              id="cron-delivery-account-id"
                              .value=${e.form.deliveryAccountId}
                              list="cron-delivery-account-suggestions"
                              ?disabled=${F!==`announce`}
                              @input=${t=>e.onFormChange({deliveryAccountId:t.target.value})}
                              placeholder="default"
                            />
                            <div class="cron-help">
                              Optional channel account ID for multi-account setups.
                            </div>
                          </label>
                          <label class="field checkbox cron-checkbox cron-span-2">
                            <input
                              type="checkbox"
                              .checked=${e.form.payloadLightContext}
                              @change=${t=>e.onFormChange({payloadLightContext:t.target.checked})}
                            />
                            <span class="field-checkbox__label">Light context</span>
                            <div class="cron-help">
                              Use lightweight bootstrap context for this agent job.
                            </div>
                          </label>
                          <label class="field">
                            ${O(i(`cron.form.model`))}
                            <input
                              id="cron-payload-model"
                              .value=${e.form.payloadModel}
                              list="cron-model-suggestions"
                              @input=${t=>e.onFormChange({payloadModel:t.target.value})}
                              placeholder=${i(`cron.form.modelPlaceholder`)}
                            />
                            <div class="cron-help">${i(`cron.form.modelHelp`)}</div>
                          </label>
                          <label class="field">
                            ${O(i(`cron.form.thinking`))}
                            <input
                              id="cron-payload-thinking"
                              .value=${e.form.payloadThinking}
                              list="cron-thinking-suggestions"
                              @input=${t=>e.onFormChange({payloadThinking:t.target.value})}
                              placeholder=${i(`cron.form.thinkingPlaceholder`)}
                            />
                            <div class="cron-help">${i(`cron.form.thinkingHelp`)}</div>
                          </label>
                        `:n}
                    ${o?t`
                          <label class="field cron-span-2">
                            ${O(`Failure alerts`)}
                            <select
                              .value=${e.form.failureAlertMode}
                              @change=${t=>e.onFormChange({failureAlertMode:t.target.value})}
                            >
                              <option value="inherit">Inherit global setting</option>
                              <option value="disabled">Disable for this job</option>
                              <option value="custom">Custom per-job settings</option>
                            </select>
                            <div class="cron-help">
                              Control when this job sends repeated-failure alerts.
                            </div>
                          </label>
                          ${e.form.failureAlertMode===`custom`?t`
                                <label class="field">
                                  ${O(`Alert after`)}
                                  <input
                                    id="cron-failure-alert-after"
                                    .value=${e.form.failureAlertAfter}
                                    aria-invalid=${e.fieldErrors.failureAlertAfter?`true`:`false`}
                                    aria-describedby=${r(e.fieldErrors.failureAlertAfter?C(`failureAlertAfter`):void 0)}
                                    @input=${t=>e.onFormChange({failureAlertAfter:t.target.value})}
                                    placeholder="2"
                                  />
                                  <div class="cron-help">Consecutive errors before alerting.</div>
                                  ${j(e.fieldErrors.failureAlertAfter,C(`failureAlertAfter`))}
                                </label>
                                <label class="field">
                                  ${O(`Cooldown (seconds)`)}
                                  <input
                                    id="cron-failure-alert-cooldown-seconds"
                                    .value=${e.form.failureAlertCooldownSeconds}
                                    aria-invalid=${e.fieldErrors.failureAlertCooldownSeconds?`true`:`false`}
                                    aria-describedby=${r(e.fieldErrors.failureAlertCooldownSeconds?C(`failureAlertCooldownSeconds`):void 0)}
                                    @input=${t=>e.onFormChange({failureAlertCooldownSeconds:t.target.value})}
                                    placeholder="3600"
                                  />
                                  <div class="cron-help">Minimum seconds between alerts.</div>
                                  ${j(e.fieldErrors.failureAlertCooldownSeconds,C(`failureAlertCooldownSeconds`))}
                                </label>
                                <label class="field">
                                  ${O(`Alert channel`)}
                                  <select
                                    .value=${e.form.failureAlertChannel||`last`}
                                    @change=${t=>e.onFormChange({failureAlertChannel:t.target.value})}
                                  >
                                    ${c.map(n=>t`<option value=${n}>
                                          ${b(e,n)}
                                        </option>`)}
                                  </select>
                                </label>
                                <label class="field">
                                  ${O(`Alert to`)}
                                  <input
                                    .value=${e.form.failureAlertTo}
                                    list="cron-delivery-to-suggestions"
                                    @input=${t=>e.onFormChange({failureAlertTo:t.target.value})}
                                    placeholder="+1555... or chat id"
                                  />
                                  <div class="cron-help">
                                    Optional recipient override for failure alerts.
                                  </div>
                                </label>
                                <label class="field">
                                  ${O(`Alert mode`)}
                                  <select
                                    .value=${e.form.failureAlertDeliveryMode||`announce`}
                                    @change=${t=>e.onFormChange({failureAlertDeliveryMode:t.target.value})}
                                  >
                                    <option value="announce">Announce (via channel)</option>
                                    <option value="webhook">Webhook (HTTP POST)</option>
                                  </select>
                                </label>
                                <label class="field">
                                  ${O(`Alert account ID`)}
                                  <input
                                    .value=${e.form.failureAlertAccountId}
                                    @input=${t=>e.onFormChange({failureAlertAccountId:t.target.value})}
                                    placeholder="Account ID for multi-account setups"
                                  />
                                </label>
                              `:n}
                        `:n}
                    ${F===`none`?n:t`
                          <label class="field checkbox cron-checkbox cron-span-2">
                            <input
                              type="checkbox"
                              .checked=${e.form.deliveryBestEffort}
                              @change=${t=>e.onFormChange({deliveryBestEffort:t.target.checked})}
                            />
                            <span class="field-checkbox__label"
                              >${i(`cron.form.bestEffortDelivery`)}</span
                            >
                            <div class="cron-help">${i(`cron.form.bestEffortHelp`)}</div>
                          </label>
                        `}
                  </div>
                </details>
              </div>
              ${V?t`
                    <div
                      class="cron-form-status"
                      role="status"
                      aria-live="polite"
                      ?hidden=${L}
                    >
                      <div class="cron-form-status__title">${i(`cron.form.cantAddYet`)}</div>
                      <div class="cron-help">${i(`cron.form.fillRequired`)}</div>
                      <ul class="cron-form-status__list">
                        ${z.map(e=>t`
                            <li>
                              <button
                                type="button"
                                class="cron-form-status__link"
                                @click=${()=>D(e.inputId)}
                              >
                                ${e.label}: ${i(e.message)}
                              </button>
                            </li>
                          `)}
                      </ul>
                    </div>
                  `:n}
              <div class="row cron-form-actions" ?hidden=${L}>
                <button
                  class="btn primary"
                  ?disabled=${e.busy||!e.canSubmit}
                  @click=${e.onAdd}
                >
                  ${e.busy?i(`cron.form.saving`):i(a?`cron.form.saveChanges`:`cron.form.addJob`)}
                </button>
                ${G?t`
                      <div class="cron-submit-reason" aria-live="polite">
                        ${G}
                      </div>
                    `:n}
                ${a?t`
                      <button class="btn" ?disabled=${e.busy} @click=${e.onCancelEdit}>
                        ${i(`cron.form.cancel`)}
                      </button>
                    `:n}
              </div>
            </section>
          </div>
        `:n}
    ${S(`cron-agent-suggestions`,e.agentSuggestions)}
    ${S(`cron-model-suggestions`,e.modelSuggestions)}
    ${S(`cron-thinking-suggestions`,e.thinkingSuggestions)}
    ${S(`cron-tz-suggestions`,e.timezoneSuggestions)}
    ${S(`cron-delivery-to-suggestions`,e.deliveryToSuggestions)}
    ${S(`cron-delivery-account-suggestions`,e.accountSuggestions)}
  `}function A(e){let n=e.form;return n.scheduleKind===`at`?t`
      <label class="field cron-span-2" style="margin-top: 12px;">
        ${O(i(`cron.form.runAt`),!0)}
        <input
          id="cron-schedule-at"
          type="datetime-local"
          .value=${n.scheduleAt}
          aria-invalid=${e.fieldErrors.scheduleAt?`true`:`false`}
          aria-describedby=${r(e.fieldErrors.scheduleAt?C(`scheduleAt`):void 0)}
          @input=${t=>e.onFormChange({scheduleAt:t.target.value})}
        />
        ${j(e.fieldErrors.scheduleAt,C(`scheduleAt`))}
      </label>
    `:n.scheduleKind===`every`?t`
      <div class="form-grid cron-form-grid" style="margin-top: 12px;">
        <label class="field">
          ${O(i(`cron.form.every`),!0)}
          <input
            id="cron-every-amount"
            .value=${n.everyAmount}
            aria-invalid=${e.fieldErrors.everyAmount?`true`:`false`}
            aria-describedby=${r(e.fieldErrors.everyAmount?C(`everyAmount`):void 0)}
            @input=${t=>e.onFormChange({everyAmount:t.target.value})}
            placeholder=${i(`cron.form.everyAmountPlaceholder`)}
          />
          ${j(e.fieldErrors.everyAmount,C(`everyAmount`))}
        </label>
        <label class="field">
          <span>${i(`cron.form.unit`)}</span>
          <select
            .value=${n.everyUnit}
            @change=${t=>e.onFormChange({everyUnit:t.target.value})}
          >
            <option value="minutes">${i(`cron.form.minutes`)}</option>
            <option value="hours">${i(`cron.form.hours`)}</option>
            <option value="days">${i(`cron.form.days`)}</option>
          </select>
        </label>
      </div>
    `:t`
    <div class="form-grid cron-form-grid" style="margin-top: 12px;">
      <label class="field">
        ${O(i(`cron.form.expression`),!0)}
        <input
          id="cron-cron-expr"
          .value=${n.cronExpr}
          aria-invalid=${e.fieldErrors.cronExpr?`true`:`false`}
          aria-describedby=${r(e.fieldErrors.cronExpr?C(`cronExpr`):void 0)}
          @input=${t=>e.onFormChange({cronExpr:t.target.value})}
          placeholder=${i(`cron.form.expressionPlaceholder`)}
        />
        ${j(e.fieldErrors.cronExpr,C(`cronExpr`))}
      </label>
      <label class="field">
        <span>${i(`cron.form.timezoneOptional`)}</span>
        <input
          .value=${n.cronTz}
          list="cron-tz-suggestions"
          @input=${t=>e.onFormChange({cronTz:t.target.value})}
          placeholder=${i(`cron.form.timezonePlaceholder`)}
        />
        <div class="cron-help">${i(`cron.form.timezoneHelp`)}</div>
      </label>
      <div class="cron-help cron-span-2">${i(`cron.form.jitterHelp`)}</div>
    </div>
  `}function j(e,a){return e?t`<div id=${r(a)} class="cron-help cron-error">${i(e)}</div>`:n}function M(e,r){let a=`list-item list-item-clickable cron-job${r.runsJobId===e.id?` list-item-selected`:``}`,o=t=>{r.onLoadRuns(e.id),t()};return t`
    <div class=${a} @click=${()=>r.onLoadRuns(e.id)}>
      <div class="cron-job-header">
        <div class="list-main">
          <div class="list-title">${e.name}</div>
          <div class="list-sub">${p(e)}</div>
          ${e.agentId?t`<div class="muted cron-job-agent">
                ${i(`cron.jobDetail.agent`)}: ${e.agentId}
              </div>`:n}
        </div>
        <div class="list-meta">${L(e)}</div>
      </div>
      ${N(e)}
      <div class="cron-job-footer">
        <div class="chip-row cron-job-chips">
          <span class=${`chip ${e.enabled?`chip-ok`:`chip-danger`}`}>
            ${e.enabled?i(`cron.jobList.enabled`):i(`cron.jobList.disabled`)}
          </span>
          <span class="chip">${e.sessionTarget}</span>
          <span class="chip">${e.wakeMode}</span>
        </div>
        <div class="row cron-job-actions">
          <button
            class="btn"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),o(()=>r.onEdit(e))}}
          >
            ${i(`cron.jobList.edit`)}
          </button>
          <button
            class="btn"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),o(()=>r.onClone(e))}}
          >
            ${i(`cron.jobList.clone`)}
          </button>
          <button
            class="btn"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),o(()=>r.onToggle(e,!e.enabled))}}
          >
            ${e.enabled?i(`cron.jobList.disable`):i(`cron.jobList.enable`)}
          </button>
          <button
            class="btn"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),o(()=>r.onRun(e,`force`))}}
          >
            ${i(`cron.jobList.run`)}
          </button>
          <button
            class="btn"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),o(()=>r.onRun(e,`due`))}}
          >
            Run if due
          </button>
          <button
            class="btn"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),r.onLoadRuns(e.id)}}
          >
            ${i(`cron.jobList.history`)}
          </button>
          <button
            class="btn danger"
            ?disabled=${r.busy}
            @click=${t=>{t.stopPropagation(),o(()=>r.onRemove(e))}}
          >
            ${i(`cron.jobList.remove`)}
          </button>
        </div>
      </div>
    </div>
  `}function N(r){let a=o(r);if(!a)return t``;if(a.kind===`systemEvent`)return t`<div class="cron-job-detail">
      <span class="cron-job-detail-label">${i(`cron.jobDetail.system`)}</span>
      <span class="muted cron-job-detail-value">${a.text}</span>
    </div>`;let s=r.delivery,c=s?.mode===`webhook`?s.to?` (${s.to})`:``:s?.channel||s?.to?` (${s.channel??`last`}${s.to?` -> ${s.to}`:``})`:``;return t`
    <div class="cron-job-detail">
      <div class="cron-job-detail-section">
        <span class="cron-job-detail-label">${i(`cron.jobDetail.prompt`)}</span>
        <div class="muted cron-job-detail-value chat-text" @click=${P}>
          ${e(l(a.message))}
        </div>
      </div>
      ${s?t`<div class="cron-job-detail-section">
            <span class="cron-job-detail-label">${i(`cron.jobDetail.delivery`)}</span>
            <span class="muted cron-job-detail-value">${s.mode}${c}</span>
          </div>`:n}
    </div>
  `}function P(e){e.target?.closest(`a,button,input,textarea,select,summary,[role='button'],[role='link']`)&&e.stopPropagation()}function F(e){return typeof e!=`number`||!Number.isFinite(e)?i(`common.na`):c(e)}function I(e,t=Date.now()){let n=c(e);return i(e>t?`cron.runEntry.next`:`cron.runEntry.due`,{rel:n})}function L(e){let n=a(e),r=n===`ok`?`cron-job-status-ok`:n===`error`?`cron-job-status-error`:n===`skipped`?`cron-job-status-skipped`:`cron-job-status-na`,o=i(n===`ok`?`cron.runs.runStatusOk`:n===`error`?`cron.runs.runStatusError`:n===`skipped`?`cron.runs.runStatusSkipped`:`cron.runs.runStatusUnknown`),c=e.state?.nextRunAtMs,l=e.state?.lastRunAtMs;return t`
    <div class="cron-job-state">
      <div class="cron-job-state-row">
        <span class="cron-job-state-key">${i(`cron.jobState.status`)}</span>
        <span class=${`cron-job-status-pill ${r}`}>${o}</span>
      </div>
      <div class="cron-job-state-row">
        <span class="cron-job-state-key">${i(`cron.jobState.next`)}</span>
        <span class="cron-job-state-value" title=${s(c)}>
          ${F(c)}
        </span>
      </div>
      <div class="cron-job-state-row">
        <span class="cron-job-state-key">${i(`cron.jobState.last`)}</span>
        <span class="cron-job-state-value" title=${s(l)}>
          ${F(l)}
        </span>
      </div>
    </div>
  `}function R(e){switch(e){case`ok`:return i(`cron.runs.runStatusOk`);case`error`:return i(`cron.runs.runStatusError`);case`skipped`:return i(`cron.runs.runStatusSkipped`);default:return i(`cron.runs.runStatusUnknown`)}}function z(e){switch(e){case`delivered`:return i(`cron.runs.deliveryDelivered`);case`not-delivered`:return i(`cron.runs.deliveryNotDelivered`);case`not-requested`:return i(`cron.runs.deliveryNotRequested`);case`unknown`:return i(`cron.runs.deliveryUnknown`);default:return i(`cron.runs.deliveryUnknown`)}}function B(r,a,o){let c=typeof r.sessionKey==`string`&&r.sessionKey.trim().length>0?`${m(`chat`,a)}?session=${encodeURIComponent(r.sessionKey)}`:null,u=R(r.status??`unknown`),d=z(r.deliveryStatus??`not-requested`),f=r.usage,p=f&&typeof f.total_tokens==`number`?`${f.total_tokens} tokens`:f&&typeof f.input_tokens==`number`&&typeof f.output_tokens==`number`?`${f.input_tokens} in / ${f.output_tokens} out`:null,h=r.summary||r.error||i(`cron.runEntry.noSummary`),g=!!r.error&&!!r.summary;return t`
    <div class="list-item cron-run-entry">
      <div class="cron-run-entry__header">
        <div class="list-main cron-run-entry__main">
          <div class="list-title cron-run-entry__title">
            ${r.jobName??r.jobId}
            <span class="muted"> · ${u}</span>
          </div>
          <div class="chip-row" style="margin-top: 4px;">
            <span class="chip">${d}</span>
            ${r.model?t`<span class="chip">${r.model}</span>`:n}
            ${r.provider?t`<span class="chip">${r.provider}</span>`:n}
            ${p?t`<span class="chip">${p}</span>`:n}
          </div>
        </div>
        <div class="list-meta cron-run-entry__meta">
          <div>${s(r.ts)}</div>
          ${typeof r.runAtMs==`number`?t`<div class="muted">${i(`cron.runEntry.runAt`)} ${s(r.runAtMs)}</div>`:n}
          <div class="muted">${r.durationMs??0}ms</div>
          ${typeof r.nextRunAtMs==`number`?t`<div class="muted">${I(r.nextRunAtMs)}</div>`:n}
          ${c?t`<div>
                <a
                  class="session-link"
                  href=${c}
                  @click=${e=>{e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||o&&r.sessionKey&&(e.preventDefault(),o(r.sessionKey))}}
                  >${i(`cron.runEntry.openRunChat`)}</a
                >
              </div>`:n}
          ${g?t`<div class="muted">${r.error}</div>`:n}
          ${r.deliveryError?t`<div class="muted">${r.deliveryError}</div>`:n}
        </div>
      </div>
      <div class="cron-run-entry__body chat-text">
        ${e(l(h))}
      </div>
    </div>
  `}export{k as renderCron};
//# sourceMappingURL=cron-Cfs5zw2Y.js.map