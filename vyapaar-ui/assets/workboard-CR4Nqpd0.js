import{m as e,p as t}from"./lit-runtime-gkTRPNbC.js";import{o as n}from"./string-coerce-DwnRzrPh.js";import{A as r,C as i,D as a,E as o,M as s,N as c,O as l,S as u,T as d,b as f,j as p,k as m,v as h,w as g,x as _,y as v,z as y}from"./index-DRTyMBOr.js";var b=[{id:`bugfix`,title:`Fix: `,notes:`Symptom:
Cause:
Acceptance:
Proof:`,labels:`fix, test`,priority:`high`},{id:`docs`,title:`Docs: `,notes:`Page:
Change:
Source proof:`,labels:`docs`,priority:`normal`},{id:`release`,title:`Release: `,notes:`Scope:
Verification:
Closeout:`,labels:`release`,priority:`urgent`},{id:`pr_review`,title:`Review PR `,notes:`Surface:
Risks:
Proof:`,labels:`review`,priority:`normal`},{id:`plugin`,title:`Plugin: `,notes:`Boundary:
Config/docs:
Tests:`,labels:`plugin`,priority:`normal`}];function x(e){return n(`workboard.status.${e}`)}function S(e){return e?y(e,{month:`short`,day:`numeric`},``):``}function C(e){return e.canWrite!==!1}function w(e){switch(e.kind){case`created`:return n(`workboard.eventCreated`);case`edited`:return n(`workboard.eventEdited`);case`moved`:return e.toStatus?n(`workboard.eventMovedTo`,{status:x(e.toStatus)}):n(`workboard.eventMoved`);case`linked`:return n(`workboard.eventLinked`);case`specified`:return n(`workboard.eventSpecified`);case`decomposed`:return n(`workboard.eventDecomposed`);case`claimed`:return n(`workboard.eventClaimed`);case`heartbeat`:return n(`workboard.eventHeartbeat`);case`execution_updated`:return n(`workboard.eventExecutionUpdated`);case`attempt_started`:return n(`workboard.eventAttemptStarted`);case`attempt_updated`:return n(`workboard.eventAttemptUpdated`);case`comment_added`:return n(`workboard.eventCommentAdded`);case`link_added`:return n(`workboard.eventLinkAdded`);case`proof_added`:return n(`workboard.eventProofAdded`);case`artifact_added`:return n(`workboard.eventArtifactAdded`);case`attachment_added`:return n(`workboard.eventAttachmentAdded`);case`diagnostic`:return n(`workboard.eventDiagnostic`);case`notification`:return n(`workboard.eventNotification`);case`dispatch`:return n(`workboard.eventDispatch`);case`orchestration`:return n(`workboard.eventOrchestration`);case`protocol_violation`:return n(`workboard.eventProtocolViolation`);case`archived`:return n(`workboard.eventArchived`);case`unarchived`:return n(`workboard.eventUnarchived`);case`stale`:return n(`workboard.eventStale`)}return``}function T(r){let i=(r.events??[]).toReversed().slice(0,4);return i.length===0?t:e`
    <ol class="workboard-events" aria-label=${n(`workboard.eventsLabel`)}>
      ${i.map(t=>e`
          <li>
            <span>${w(t)}</span>
            <time>${S(t.at)}</time>
          </li>
        `)}
    </ol>
  `}function E(r,i){let a=r.metadata,o=[];return a?.templateId&&o.push(e`<span>${n(`workboard.template.${a.templateId}`)}</span>`),(i??r.taskId)&&o.push(e`<span>${n(`workboard.badgeTaskLinked`)}</span>`),a?.failureCount&&o.push(e`
      <span class="workboard-card__badge--warning">
        ${h.alertTriangle}${n(`workboard.badgeFailures`,{count:String(a.failureCount)})}
      </span>
    `),a?.comments?.length&&o.push(e`<span
        >${n(`workboard.badgeComments`,{count:String(a.comments.length)})}</span
      >`),a?.proof?.length&&o.push(e`<span>${n(`workboard.badgeProof`,{count:String(a.proof.length)})}</span>`),a?.claim&&o.push(e`<span>${n(`workboard.badgeClaimed`,{owner:a.claim.ownerId})}</span>`),a?.diagnostics?.length&&o.push(e`<span class="workboard-card__badge--warning">
        ${h.alertTriangle}${n(`workboard.badgeDiagnostics`,{count:String(a.diagnostics.length)})}
      </span>`),a?.stale&&o.push(e`<span class="workboard-card__badge--warning"
        >${h.alertTriangle}${n(`workboard.badgeStale`)}</span
      >`),o.length===0?t:e` <div class="workboard-card__badges">${o}</div> `}function D(e,t){if(t.priority!==`all`&&e.priority!==t.priority)return!1;let n=t.query.trim().toLowerCase();return n?[e.title,e.notes,e.agentId,e.sessionKey,e.execution?.engine,e.execution?.mode,e.execution?.model,e.execution?.sessionKey,e.metadata?.templateId,e.metadata?.automation?.tenant,e.metadata?.automation?.idempotencyKey,e.metadata?.automation?.workspace?.kind,e.metadata?.automation?.workspace?.path,e.metadata?.automation?.workspace?.branch,...e.metadata?.automation?.skills??[],...e.metadata?.automation?.createdCardIds??[],...(e.metadata?.comments??[]).map(e=>e.body),...(e.metadata?.links??[]).flatMap(e=>[e.title,e.url,e.targetCardId]),...(e.metadata?.proof??[]).flatMap(e=>[e.label,e.command,e.url,e.note]),...(e.metadata?.artifacts??[]).flatMap(e=>[e.label,e.url,e.path,e.mimeType]),...(e.metadata?.attachments??[]).flatMap(e=>[e.fileName,e.mimeType,e.note]),...(e.metadata?.workerLogs??[]).map(e=>e.message),e.metadata?.workerProtocol?.state,e.metadata?.workerProtocol?.detail,e.metadata?.claim?.ownerId,...(e.metadata?.diagnostics??[]).flatMap(e=>[e.kind,e.severity,e.title,e.detail]),...(e.metadata?.notifications??[]).map(e=>e.message),...e.labels].filter(e=>typeof e==`string`).some(e=>e.toLowerCase().includes(n)):!0}function O(e,t){let n=e.filter(e=>e.status===t).map(e=>e.position);return(n.length?Math.max(...n):0)+1e3}function k(e){if(e.archived||e.kind===`global`)return!1;let t=[e.key,e.label,e.displayName].filter(e=>typeof e==`string`).join(`:`).toLowerCase();return!/(^|:)heartbeat(:|$)/.test(t)}function A(e){return e.target instanceof Element?!!e.target.closest(`button, a, input, select, textarea`):!1}function j(e,t){return e?.name??e?.identity?.name??e?.id??t}function M(e,t){return e.agentId?.trim()||t?.defaultId||``}function N(e,t){let n=M(e,t);return n?t?.agents.find(e=>e.id===n):void 0}function P(e,t){let r=e.agentId?.trim()||n(`workboard.defaultAgent`);return j(N(e,t),r)}function F(e,t,n){if(n===`all`)return!0;let r=e.agentId?.trim();return n===`default`?!r:r===n||!r&&t?.defaultId===n}function ee(e,t){let r=new Set,i=[{id:`all`,label:n(`workboard.allAgents`)},{id:`default`,label:n(`workboard.defaultAgent`)}];for(let e of t?.agents??[])r.has(e.id)||(r.add(e.id),i.push({id:e.id,label:j(e,e.id)}));for(let t of e){let e=t.agentId?.trim();!e||r.has(e)||(r.add(e),i.push({id:e,label:e}))}return i}function I(e){return n(e===`codex`?`workboard.engineOpenAI`:`workboard.engineClaude`)}function L(e,t,r){if(!r)return null;let i=N(t,e.agentsList),a=i?.agentRuntime?.id?.trim();if(!a)return null;let o=a.toLowerCase();return o===`openclaw`||o===`pi`?null:n(`workboard.engineDisabledRuntime`,{agent:j(i,t.agentId??n(`workboard.defaultAgent`)),runtime:a})}function R(t,r){let i=P(r,t.agentsList);return e`<span class="workboard-agent-chip" title=${r.agentId?n(`workboard.agentLinked`,{agent:i}):n(`workboard.agentDefaultLinked`,{agent:i})}>${i}</span>`}function z(t){return e`
    <span class="workboard-engine-mark workboard-engine-mark--${t}" aria-hidden="true">
      ${t===`codex`?`OpenAI`:`Claude`}
    </span>
  `}function B(e,t){e.detailCardId=t.id,e.detailCommentBody=``}function V(e){e.draftOpen=!1,e.editingCardId=null,e.draftTitle=``,e.draftNotes=``,e.draftStatus=`todo`,e.draftPriority=`normal`,e.draftLabels=``,e.draftAgentId=``,e.draftSessionKey=``,e.draftTemplateId=``,e.draftCommentBody=``}function te(e){V(e),e.draftOpen=!0}function ne(e,t){e.draftOpen=!0,e.editingCardId=t.id,e.draftTitle=t.title,e.draftNotes=t.notes??``,e.draftStatus=t.status,e.draftPriority=t.priority,e.draftLabels=t.labels.join(`, `),e.draftAgentId=t.agentId??``,e.draftSessionKey=t.sessionKey??``,e.draftTemplateId=t.metadata?.templateId??``,e.draftCommentBody=``}function re(e,t){let n=b.find(e=>e.id===t);n&&(e.draftTemplateId=n.id,e.draftTitle=n.title,e.draftNotes=n.notes,e.draftLabels=n.labels,e.draftPriority=n.priority)}function H(i){let o=a(i.host),s=i.agentsList?.agents??[],c=i.sessions.filter(k);if(!o.draftOpen)return t;let l=!!o.editingCardId,u=(o.editingCardId?o.cards.find(e=>e.id===o.editingCardId)??null:null)?.metadata?.comments??[],d=l&&o.busyCardId===o.editingCardId;return e`
    <div
      class="workboard-modal"
      role="presentation"
      @click=${e=>{e.target===e.currentTarget&&(V(o),i.onRequestUpdate?.())}}
    >
      <form
        class="workboard-draft"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workboard-card-modal-title"
        @submit=${e=>{e.preventDefault(),!(o.loading||d)&&r({host:i.host,client:i.client,requestUpdate:i.onRequestUpdate})}}
      >
        <div class="workboard-modal__header">
          <div>
            <h2 id="workboard-card-modal-title">
              ${n(l?`workboard.editCard`:`workboard.newCard`)}
            </h2>
            <p>${n(l?`workboard.editCardHelp`:`workboard.newCardHelp`)}</p>
          </div>
          <button
            class="btn btn--icon workboard-card__icon"
            type="button"
            title=${n(`common.cancel`)}
            @click=${()=>{V(o),i.onRequestUpdate?.()}}
          >
            ${h.x}
          </button>
        </div>
        ${l?t:e`
              <div class="workboard-template-strip" aria-label=${n(`workboard.templatesLabel`)}>
                ${b.map(t=>e`
                    <button
                      class="btn btn--xs ${o.draftTemplateId===t.id?`workboard-template-strip__button--active`:``}"
                      type="button"
                      @click=${()=>{re(o,t.id),i.onRequestUpdate?.()}}
                    >
                      ${n(`workboard.template.${t.id}`)}
                    </button>
                  `)}
              </div>
            `}
        <div class="workboard-draft__main">
          <label class="workboard-field">
            <span>${n(`workboard.fieldTitle`)}</span>
            <input
              class="input workboard-draft__title"
              placeholder=${n(`workboard.titlePlaceholder`)}
              .value=${o.draftTitle}
              @input=${e=>{o.draftTitle=e.currentTarget.value,i.onRequestUpdate?.()}}
            />
          </label>
          <label class="workboard-field">
            <span>${n(`workboard.fieldNotes`)}</span>
            <textarea
              class="input workboard-draft__notes"
              placeholder=${n(`workboard.notesPlaceholder`)}
              .value=${o.draftNotes}
              @input=${e=>{o.draftNotes=e.currentTarget.value,i.onRequestUpdate?.()}}
            ></textarea>
          </label>
        </div>
        <div class="workboard-draft__meta">
          <label class="workboard-field">
            <span>${n(`workboard.fieldStatus`)}</span>
            <select
              class="input"
              .value=${o.draftStatus}
              @change=${e=>{o.draftStatus=e.currentTarget.value,i.onRequestUpdate?.()}}
            >
              ${o.statuses.map(t=>e`<option value=${t}>${x(t)}</option>`)}
            </select>
          </label>
          <label class="workboard-field">
            <span>${n(`workboard.fieldPriority`)}</span>
            <select
              class="input"
              .value=${o.draftPriority}
              @change=${e=>{o.draftPriority=e.currentTarget.value,i.onRequestUpdate?.()}}
            >
              ${v.map(t=>e`<option value=${t}>${t}</option>`)}
            </select>
          </label>
          <label class="workboard-field">
            <span>${n(`workboard.fieldAgent`)}</span>
            <select
              class="input"
              .value=${o.draftAgentId}
              @change=${e=>{o.draftAgentId=e.currentTarget.value,i.onRequestUpdate?.()}}
            >
              <option value="">${n(`workboard.defaultAgent`)}</option>
              ${s.map(t=>e`<option value=${t.id}>
                    ${t.name??t.identity?.name??t.id}
                  </option>`)}
            </select>
          </label>
          <label class="workboard-field">
            <span>${n(`workboard.fieldSession`)}</span>
            <select
              class="input"
              .value=${o.draftSessionKey}
              @change=${e=>{o.draftSessionKey=e.currentTarget.value,i.onRequestUpdate?.()}}
            >
              <option value="">${n(`workboard.noLinkedSession`)}</option>
              ${c.map(t=>e`<option value=${t.key}>
                    ${t.displayName??t.label??t.key}
                  </option>`)}
            </select>
          </label>
          <label class="workboard-field workboard-field--wide">
            <span>${n(`workboard.fieldLabels`)}</span>
            <input
              class="input"
              placeholder=${n(`workboard.labelsPlaceholder`)}
              .value=${o.draftLabels}
              @input=${e=>{o.draftLabels=e.currentTarget.value,i.onRequestUpdate?.()}}
            />
          </label>
        </div>
        ${l?e`
              <section
                class="workboard-field workboard-field--wide"
                aria-labelledby="workboard-card-comments-title"
              >
                <span id="workboard-card-comments-title">
                  ${n(`workboard.badgeComments`,{count:String(u.length)})}
                </span>
                ${u.length?e`
                      <ol>
                        ${u.map(t=>e`<li>${t.body}</li>`)}
                      </ol>
                    `:t}
                <textarea
                  class="input workboard-comments__input"
                  aria-labelledby="workboard-card-comments-title"
                  maxlength="2000"
                  .value=${o.draftCommentBody}
                  @input=${e=>{o.draftCommentBody=e.currentTarget.value,i.onRequestUpdate?.()}}
                ></textarea>
                <div class="workboard-modal__actions">
                  <button
                    class="btn"
                    type="button"
                    ?disabled=${o.loading||d||!o.draftCommentBody.trim()}
                    @click=${()=>{f({host:i.host,client:i.client,requestUpdate:i.onRequestUpdate})}}
                  >
                    ${h.plus} ${n(`common.create`)}
                  </button>
                </div>
              </section>
            `:t}
        <div class="workboard-modal__actions">
          <button
            class="btn primary"
            ?disabled=${o.loading||d||!o.draftTitle.trim()}
          >
            ${n(l?`common.save`:`common.create`)}
          </button>
          <button
            class="btn"
            type="button"
            @click=${()=>{V(o),i.onRequestUpdate?.()}}
          >
            ${n(`common.cancel`)}
          </button>
        </div>
      </form>
    </div>
  `}function U(e){switch(e.state){case`running`:return{label:n(`workboard.lifecycleRunning`),detail:n(`workboard.lifecycleRunningDetail`),tone:`live`};case`succeeded`:return{label:n(`workboard.lifecycleDone`),detail:n(`workboard.lifecycleDoneDetail`),tone:`done`};case`failed`:return{label:n(`workboard.lifecycleNeedsReview`),detail:n(`workboard.lifecycleNeedsReviewDetail`),tone:`blocked`};case`stale`:return{label:n(`workboard.lifecycleStale`),detail:n(`workboard.lifecycleStaleDetail`),tone:`blocked`};case`idle`:return{label:n(`workboard.lifecycleLinked`),detail:n(`workboard.lifecycleIdleDetail`),tone:`idle`};case`missing`:return{label:n(`workboard.lifecycleMissing`),detail:n(`workboard.lifecycleMissingDetail`),tone:`blocked`};case`unlinked`:return{label:n(`workboard.lifecycleUnlinked`),detail:n(`workboard.lifecycleUnlinkedDetail`),tone:`idle`}}throw Error(`Unknown workboard lifecycle state.`)}function W(e){return e.status===`queued`||e.status===`running`?e.progressSummary??e.title??e.taskId:e.terminalSummary??e.error??e.progressSummary??e.title??e.taskId}function G(e,t){switch(e.status){case`queued`:case`running`:return t.state===`running`;case`completed`:return t.state===`succeeded`;case`failed`:case`cancelled`:case`timed_out`:return t.state===`failed`}return!1}function K(e){return e?.status===`queued`||e?.status===`running`}function q(e,t,n){let r=e.tasksByCardId.get(n.id),i=g(n,t),a=K(r),o=n.sessionKey??n.execution?.sessionKey;return!a&&(!o||!i)}function J(e){if(e.missing)return n(`workboard.dependencyMissing`,{parent:e.title});let t=e.status?x(e.status):n(`workboard.unknownStatus`);return`${e.title} (${t})`}function Y(e){return e.blockedParents.length===0?null:n(`workboard.dependenciesBlockedTitle`,{parents:e.blockedParents.map(J).join(`, `)})}function ie(r){if(r.parents.length===0)return t;let i=r.blockedParents.length;return e`
    <div class="workboard-dependencies" title=${Y(r)??n(`workboard.dependenciesReadyTitle`,{count:String(r.parents.length)})}>
      ${i>0?e`
            <span class="workboard-dependency workboard-dependency--blocked">
              ${h.alertTriangle}${n(`workboard.dependenciesBlocked`,{count:String(i)})}
            </span>
          `:e`
            <span class="workboard-dependency workboard-dependency--ready">
              ${n(`workboard.dependenciesReady`,{count:String(r.parents.length)})}
            </span>
          `}
    </div>
  `}function ae(r){return r.parents.length===0?t:e`
    <section class="workboard-detail__section">
      <h3>${n(`workboard.dependencies`)}</h3>
      <ul class="workboard-detail__list workboard-detail__dependencies">
        ${r.parents.map(t=>e`
            <li class=${t.done?`is-done`:`is-blocked`}>
              ${t.done?e`<span class="workboard-detail__dependency-spacer"></span>`:h.alertTriangle}
              <span>${t.title}</span>
              <span>
                ${t.missing?n(`workboard.dependencyStatusMissing`):t.status?x(t.status):n(`workboard.unknownStatus`)}
              </span>
            </li>
          `)}
      </ul>
    </section>
  `}function oe(t,r,i){let a=o(t,r,i),s=U(a),c=a.session,l=t.execution,u=a.state===`stale`,d=i?G(i,a):!1,f=i&&d?n(`workboard.taskStatus.${i.status}`):null;return e`
    <div class="workboard-card__lifecycle">
      <span class="workboard-lifecycle workboard-lifecycle--${s.tone}">
        ${f??(u||!l?s.label:`${l.engine} ${l.mode}`)}
      </span>
      <span class="workboard-card__lifecycle-detail">
        ${i&&d?W(i):u?s.detail:c?.displayName??c?.label??s.detail}
      </span>
    </div>
  `}function X(r,i,o,s,c={}){let l=a(r.host).busyCardId===i.id,u=L(r,i,o),d=l||!r.connected||!!u||!!i.metadata?.archivedAt,f=u||(o?n(s===`autonomous`?`workboard.runEngine`:`workboard.openEngine`,{engine:I(o)}):n(`workboard.runDefaultAgent`));return e`
    <button
      class="btn btn--xs workboard-card__start workboard-card__start--${s} ${c.iconOnly?`workboard-card__start--icon`:``} ${o?``:`workboard-card__start--default`}"
      type="button"
      title=${f}
      aria-label=${f}
      ?disabled=${d}
      @click=${async()=>{let e=await p({host:r.host,client:r.client,card:i,...o?{engine:o}:{},mode:s,requestUpdate:r.onRequestUpdate});e&&r.onOpenSession(e)}}
    >
      ${o?e`${z(o)}${c.iconOnly?t:e`<span
                >${n(s===`autonomous`?`workboard.run`:`workboard.open`)}</span
              >`}`:e`${s===`autonomous`?h.play:h.penLine}${c.iconOnly?t:e`<span>${n(`workboard.start`)}</span>`}`}
    </button>
  `}function se(n,r){let i=n.canModelOverride!==!1;return e`
    <div class="workboard-card__execution-controls">
      ${X(n,r,null,`autonomous`)}
      ${i?e`${X(n,r,`codex`,`autonomous`)}
          ${X(n,r,`claude`,`autonomous`)}`:t}
      ${X(n,r,`codex`,`manual`)}
      ${X(n,r,`claude`,`manual`)}
    </div>
  `}function Z(n,r){if(typeof r!=`string`&&typeof r!=`number`)return t;let i=String(r).trim();return i?e`
    <div class="workboard-detail__row">
      <span>${n}</span>
      <strong>${i}</strong>
    </div>
  `:t}function Q(n,r,i=t){let a=r.map(e=>e.trim()).filter(Boolean).slice(-6);return a.length===0?i:e`
    <section class="workboard-detail__section">
      <h3>${n}</h3>
      <ol class="workboard-detail__list">
        ${a.map(t=>e`<li>${t}</li>`)}
      </ol>
    </section>
  `}function ce(r){let i=a(r.host),s=i.detailCardId?i.cards.find(e=>e.id===i.detailCardId)??null:null;if(!s||s.metadata?.archivedAt&&!i.showArchived)return t;let c=i.tasksByCardId.get(s.id),l=o(s,r.sessions,c),u=U(l),p=c?G(c,l):!1,m=s.sessionKey??s.execution?.sessionKey,g=C(r),_=s.metadata?.comments??[],v=s.metadata?.attempts??[],y=s.metadata?.links??[],b=s.metadata?.proof??[],T=s.metadata?.artifacts??[],E=s.metadata?.attachments??[],D=s.metadata?.diagnostics??[],O=s.metadata?.workerLogs??[],k=s.metadata?.workerProtocol,A=s.metadata?.automation,j=(s.events??[]).slice(-6).toReversed(),M=i.busyCardId===s.id,N=g&&q(i,r.sessions,s),P=d(s,i.cards);return e`
    <aside class="workboard-detail-drawer" aria-label=${n(`workboard.detailTitle`)}>
      <div class="workboard-detail">
        <header class="workboard-detail__header">
          <div>
            <span class="workboard-card__priority">${s.priority}</span>
            <h2>${s.title}</h2>
          </div>
          <button
            class="btn btn--icon workboard-card__icon"
            type="button"
            title=${n(`common.cancel`)}
            @click=${()=>{i.detailCardId=null,i.detailCommentBody=``,r.onRequestUpdate?.()}}
          >
            ${h.x}
          </button>
        </header>

        <section class="workboard-detail__section">
          <div class="workboard-card__lifecycle">
            <span class="workboard-lifecycle workboard-lifecycle--${u.tone}">
              ${u.label}
            </span>
            <span class="workboard-card__lifecycle-detail">
              ${c&&p?W(c):l.session?.displayName??u.detail}
            </span>
          </div>
          <div class="workboard-detail__grid">
            ${Z(n(`workboard.fieldStatus`),x(s.status))}
            ${Z(n(`workboard.fieldAgent`),s.agentId??n(`workboard.defaultAgent`))}
            ${Z(n(`workboard.detailTask`),c?.taskId??s.taskId)}
            ${Z(n(`workboard.fieldSession`),m)}
            ${Z(n(`workboard.detailRun`),s.runId??s.execution?.runId)}
            ${Z(n(`workboard.detailUpdated`),S(s.updatedAt))}
          </div>
        </section>

        ${s.notes?e`
              <section class="workboard-detail__section">
                <h3>${n(`workboard.fieldNotes`)}</h3>
                <p>${s.notes}</p>
              </section>
            `:t}
        ${ae(P)}
        ${Q(n(`workboard.fieldLabels`),s.labels)}
        ${Q(n(`workboard.badgeAttempts`,{count:String(v.length)}),v.map(e=>[e.status,e.model,e.sessionKey,e.error].filter(Boolean).join(` - `)))}
        ${Q(n(`workboard.badgeLinks`,{count:String(y.length)}),y.map(e=>[e.type,e.title,e.targetCardId,e.url].filter(Boolean).join(` - `)))}
        ${Q(n(`workboard.detailProof`),b.map(e=>[e.status,e.label,e.command,e.url,e.note].filter(Boolean).join(` - `)))}
        ${Q(n(`workboard.badgeArtifacts`,{count:String(T.length)}),T.map(e=>[e.label,e.url,e.path,e.mimeType].filter(Boolean).join(` - `)))}
        ${Q(n(`workboard.badgeAttachments`,{count:String(E.length)}),E.map(e=>[e.fileName,e.mimeType,e.note].filter(Boolean).join(` - `)))}
        ${Q(n(`workboard.detailDiagnostics`),D.map(e=>`${e.severity}: ${e.title}`))}
        ${Q(n(`workboard.detailWorkerLogs`),O.map(e=>`${e.level}: ${e.message}`))}
        ${k?Q(n(`workboard.detailWorkerProtocol`),[k.state,k.detail??``,k.updatedAt?n(`workboard.detailUpdatedValue`,{time:S(k.updatedAt)}):``]):t}
        ${A?Q(n(`workboard.detailAutomation`),[A.tenant?n(`workboard.detailAutomationTenant`,{tenant:A.tenant}):``,A.boardId?n(`workboard.detailAutomationBoard`,{board:A.boardId}):``,A.skills?.length?n(`workboard.detailAutomationSkills`,{skills:A.skills.join(`, `)}):``,A.workspace?n(`workboard.detailAutomationWorkspace`,{workspace:[A.workspace.kind,A.workspace.path,A.workspace.branch].filter(Boolean).join(` `)}):``,A.dispatchCount?n(`workboard.badgeDispatches`,{count:String(A.dispatchCount)}):``,A.lastDispatchAt?n(`workboard.detailUpdatedValue`,{time:S(A.lastDispatchAt)}):``,A.summary?n(`workboard.detailAutomationSummary`,{summary:A.summary}):``]):t}
        ${Q(n(`workboard.eventsLabel`),j.map(e=>`${w(e)} ${S(e.at)}`))}

        <section class="workboard-detail__section">
          <h3>${n(`workboard.detailOperatorNotes`)}</h3>
          ${_.length?e`
                <ol class="workboard-detail__list">
                  ${_.slice(-6).map(t=>e`<li>${t.body}</li>`)}
                </ol>
              `:e`<p>${n(`workboard.detailNoNotes`)}</p>`}
          ${g?e`
                <textarea
                  class="input workboard-detail__note"
                  maxlength="2000"
                  placeholder=${n(`workboard.detailNotePlaceholder`)}
                  .value=${i.detailCommentBody}
                  @input=${e=>{i.detailCommentBody=e.currentTarget.value,r.onRequestUpdate?.()}}
                ></textarea>
                <button
                  class="btn"
                  type="button"
                  ?disabled=${M||!i.detailCommentBody.trim()}
                  @click=${()=>f({host:r.host,client:r.client,cardId:s.id,body:i.detailCommentBody,requestUpdate:r.onRequestUpdate})}
                >
                  ${h.plus} ${n(`workboard.detailAddNote`)}
                </button>
              `:t}
        </section>

        <div class="workboard-detail__actions">
          ${m?e`
                <button
                  class="btn"
                  type="button"
                  @click=${()=>r.onOpenSession(m)}
                >
                  ${h.messageSquare} ${n(`workboard.openSession`)}
                </button>
              `:t}
          ${N?se(r,s):t}
        </div>
      </div>
    </aside>
  `}function le(r){let i=r.lastDispatchSummary;return i?e`
    <div class="callout">
      ${n(i.started+i.failures+i.promoted+i.blocked+i.reclaimed+i.orchestrated===0?`workboard.dispatchSummaryEmpty`:`workboard.dispatchSummary`,{started:String(i.started),failures:String(i.failures),promoted:String(i.promoted),blocked:String(i.blocked),reclaimed:String(i.reclaimed),orchestrated:String(i.orchestrated)})}
    </div>
  `:t}function $(r,i){let o=a(r.host),c=o.tasksByCardId.get(i.id),l=g(i,r.sessions),f=o.busyCardId===i.id,p=o.syncingCardIds.has(i.id),m=K(c),v=m||l?.hasActiveRun===!0||l?.hasActiveRun!==!1&&l?.status===`running`,y=i.sessionKey??i.execution?.sessionKey,b=C(r),x=b&&q(o,r.sessions,i),w=!!i.metadata?.archivedAt,D=d(i,o.cards);return e`
    <article
      class="workboard-card priority-${i.priority} ${f?`workboard-card--busy`:``} ${w?`workboard-card--archived`:``} workboard-card--openable"
      role="button"
      tabindex="0"
      title=${n(`workboard.viewDetails`)}
      draggable=${b?`true`:`false`}
      @click=${e=>{A(e)||(B(o,i),r.onRequestUpdate?.())}}
      @keydown=${e=>{A(e)||e.key!==`Enter`&&e.key!==` `||(B(o,i),r.onRequestUpdate?.(),e.preventDefault())}}
      @dragstart=${e=>{if(!b){e.preventDefault();return}o.draggedCardId=i.id,e.dataTransfer?.setData(`text/plain`,i.id),e.dataTransfer?.setDragImage(e.currentTarget,16,16),r.onRequestUpdate?.()}}
      @dragend=${()=>{o.draggedCardId=null,r.onRequestUpdate?.()}}
    >
      <div class="workboard-card__top">
        <div class="workboard-card__chips">
          <span class="workboard-card__priority">${i.priority}</span>
          ${R(r,i)}
          ${w?e`<span class="workboard-card__archived">${n(`workboard.archived`)}</span>`:t}
          ${v?e`<span class="workboard-live">${n(`workboard.live`)}</span>`:t}
          ${p?e`<span class="workboard-live">${n(`common.saving`)}</span>`:t}
        </div>
        <div class="workboard-card__quick-actions">
          ${x?X(r,i,null,`autonomous`,{iconOnly:!0}):t}
          ${b&&!w?e`
                <button
                  class="btn btn--icon workboard-card__icon"
                  type="button"
                  title=${n(`workboard.editCard`)}
                  aria-label=${n(`workboard.editCard`)}
                  @click=${()=>{ne(o,i),r.onRequestUpdate?.()}}
                >
                  ${h.edit}
                </button>
              `:t}
          ${b?e`
                <button
                  class="btn btn--icon workboard-card__icon"
                  type="button"
                  title=${n(w?`workboard.unarchiveCard`:`workboard.archiveCard`)}
                  aria-label=${n(w?`workboard.unarchiveCard`:`workboard.archiveCard`)}
                  ?disabled=${f}
                  @click=${()=>_({host:r.host,client:r.client,cardId:i.id,archived:!w,requestUpdate:r.onRequestUpdate})}
                >
                  ${w?h.archiveRestore:h.archive}
                </button>
              `:t}
        </div>
      </div>
      <h3>${i.title}</h3>
      ${i.notes?e`<p>${i.notes}</p>`:t}
      ${oe(i,r.sessions,c)} ${ie(D)}
      ${i.labels.length?e`<div class="workboard-labels">
            ${i.labels.map(t=>e`<span>${t}</span>`)}
          </div>`:t}
      ${E(i,c)}
      <div class="workboard-card__meta">
        <span>${y??n(`workboard.noLinkedSession`)}</span>
        <span>${S(i.updatedAt)}</span>
      </div>
      ${T(i)}
      <div class="workboard-card__actions">
        <button
          class="btn btn--icon workboard-card__icon"
          title=${n(`workboard.viewDetails`)}
          @click=${()=>{B(o,i),r.onRequestUpdate?.()}}
        >
          ${h.panelRightOpen}
        </button>
        ${y?e`
              <button
                class="btn btn--icon workboard-card__icon"
                title=${n(`workboard.openSession`)}
                @click=${()=>r.onOpenSession(y)}
              >
                ${h.messageSquare}
              </button>
              ${b&&v?e`
                    <button
                      class="btn btn--icon workboard-card__icon"
                      title=${n(`workboard.stopSession`)}
                      ?disabled=${f||!r.connected}
                      @click=${()=>s({host:r.host,client:r.client,card:i,requestUpdate:r.onRequestUpdate})}
                    >
                      ${h.stop}
                    </button>
                  `:t}
            `:t}
        ${!y&&b&&m?e`
              <button
                class="btn btn--icon workboard-card__icon"
                title=${n(`workboard.stopSession`)}
                ?disabled=${f||!r.connected}
                @click=${()=>s({host:r.host,client:r.client,card:i,requestUpdate:r.onRequestUpdate})}
              >
                ${h.stop}
              </button>
            `:t}
        ${b?e`
              <button
                class="btn btn--icon workboard-card__icon workboard-card__delete"
                type="button"
                title=${n(`workboard.deleteCard`)}
                aria-label=${n(`workboard.deleteCard`)}
                ?disabled=${f}
                @click=${()=>u({host:r.host,client:r.client,cardId:i.id,requestUpdate:r.onRequestUpdate})}
              >
                ${h.trash}
              </button>
            `:t}
      </div>
    </article>
  `}function ue(t,r,i){let o=a(t.host),s=C(t);return e`
    <section
      class="workboard-column workboard-column--${r} ${o.draggedCardId?`workboard-column--drop`:``}"
      @dragover=${e=>{s&&o.draggedCardId&&e.preventDefault()}}
      @drop=${e=>{if(e.preventDefault(),!s)return;let n=e.dataTransfer?.getData(`text/plain`)||o.draggedCardId;n&&m({host:t.host,client:t.client,cardId:n,status:r,position:O(o.cards,r),requestUpdate:t.onRequestUpdate})}}
    >
      <div class="workboard-column__header">
        <h2>${x(r)}</h2>
        <span>${i.length}</span>
      </div>
      <div class="workboard-column__cards">
        ${i.length?i.map(e=>$(t,e)):e`<div class="workboard-empty">${n(`workboard.emptyColumn`)}</div>`}
      </div>
    </section>
  `}function de(r){let o=a(r.host);if(r.pluginEnabled&&(l({host:r.host,client:r.client,requestUpdate:r.onRequestUpdate}),c({host:r.host,client:r.client,sessions:r.sessions,canWrite:r.canWrite,requestUpdate:r.onRequestUpdate})),!r.pluginEnabled)return e`
      <section class="workboard">
        <div class="callout">
          ${n(`workboard.disabledHelpStart`)}
          <code>${n(`workboard.enableConfigKey`)}</code>${n(`workboard.disabledHelpEnd`)}
        </div>
      </section>
    `;let s=o.cards.filter(e=>o.showArchived||!e.metadata?.archivedAt).filter(e=>F(e,r.agentsList,o.agentFilter)).filter(e=>D(e,{query:o.query,priority:o.priorityFilter})),u=C(r),d=ee(o.cards,r.agentsList),f=new Map;for(let e of o.statuses)f.set(e,[]);for(let e of s)f.get(e.status)?.push(e);return e`
    <section class="workboard">
      <div class="workboard-toolbar">
        <div class="workboard-toolbar__filters">
          <input
            class="input"
            type="search"
            title=${n(`workboard.searchPlaceholder`)}
            placeholder=${n(`workboard.searchPlaceholder`)}
            .value=${o.query}
            @input=${e=>{o.query=e.currentTarget.value,r.onRequestUpdate?.()}}
          />
          <select
            class="input"
            title=${n(`workboard.allPriorities`)}
            .value=${o.priorityFilter}
            @change=${e=>{o.priorityFilter=e.currentTarget.value,r.onRequestUpdate?.()}}
          >
            <option value="all">${n(`workboard.allPriorities`)}</option>
            ${v.map(t=>e`<option value=${t}>${t}</option>`)}
          </select>
          <select
            class="input"
            title=${n(`workboard.agentFilter`)}
            .value=${o.agentFilter}
            @change=${e=>{o.agentFilter=e.currentTarget.value,r.onRequestUpdate?.()}}
          >
            ${d.map(t=>e`<option value=${t.id}>${t.label}</option>`)}
          </select>
          <button
            class="btn workboard-archive-toggle ${o.showArchived?`active`:``}"
            type="button"
            title=${o.showArchived?n(`workboard.hideArchived`):n(`workboard.showArchived`)}
            aria-pressed=${o.showArchived}
            @click=${()=>{o.showArchived=!o.showArchived,r.onRequestUpdate?.()}}
          >
            ${o.showArchived?h.eye:h.eyeOff}
            ${o.showArchived?n(`workboard.hideArchivedShort`):n(`workboard.showArchivedShort`)}
          </button>
          <div class="workboard-layout-toggle" role="group" aria-label=${n(`workboard.layout`)}>
            <button
              class="btn btn--icon ${o.layout===`compact`?`active`:``}"
              type="button"
              title=${n(`workboard.layoutCompact`)}
              aria-label=${n(`workboard.layoutCompact`)}
              aria-pressed=${o.layout===`compact`}
              @click=${()=>{o.layout=`compact`,r.onRequestUpdate?.()}}
            >
              ${h.layoutCompact}
            </button>
            <button
              class="btn btn--icon ${o.layout===`comfortable`?`active`:``}"
              type="button"
              title=${n(`workboard.layoutComfortable`)}
              aria-label=${n(`workboard.layoutComfortable`)}
              aria-pressed=${o.layout===`comfortable`}
              @click=${()=>{o.layout=`comfortable`,r.onRequestUpdate?.()}}
            >
              ${h.layoutComfortable}
            </button>
          </div>
        </div>
        <div class="workboard-toolbar__actions">
          <button
            class="btn"
            type="button"
            title=${n(`common.refresh`)}
            ?disabled=${o.loading}
            @click=${()=>l({host:r.host,client:r.client,requestUpdate:r.onRequestUpdate,force:!0})}
          >
            ${o.loading?n(`common.refreshing`):n(`common.refresh`)}
          </button>
          ${u?e`
                <button
                  class="btn"
                  type="button"
                  title=${n(`workboard.dispatch`)}
                  ?disabled=${o.loading}
                  @click=${()=>i({host:r.host,client:r.client,requestUpdate:r.onRequestUpdate})}
                >
                  ${h.zap} ${n(`workboard.dispatch`)}
                </button>
              `:t}
          ${u?e`
                <button
                  class="btn primary"
                  type="button"
                  title=${n(`workboard.newCard`)}
                  @click=${()=>{te(o),r.onRequestUpdate?.()}}
                >
                  ${h.plus} ${n(`workboard.newCard`)}
                </button>
              `:t}
        </div>
      </div>
      ${o.error?e`<div class="callout danger">${o.error}</div>`:t}
      ${le(o)} ${H(r)} ${ce(r)}
      <div class="workboard-board workboard-board--${o.layout}">
        ${o.statuses.map(e=>ue(r,e,f.get(e)??[]))}
      </div>
    </section>
  `}export{de as renderWorkboard};
//# sourceMappingURL=workboard-CR4Nqpd0.js.map