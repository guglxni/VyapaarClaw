import{i as e,m as t,o as n,p as r}from"./lit-runtime-gkTRPNbC.js";import{o as i,t as a}from"./string-coerce-DwnRzrPh.js";import{P as o,R as s,_ as c,g as l}from"./index-DRTyMBOr.js";import{i as u,n as d,r as f,t as p}from"./skills-shared-CyESuAoW.js";function m(e){return e?l(e,window.location.href):null}function h(e){!(e instanceof HTMLDialogElement)||e.open||(e.isConnected?e.showModal():queueMicrotask(()=>{e.isConnected&&!e.open&&e.showModal()}))}var g=[{id:`all`,label:`All`},{id:`ready`,label:`Ready`},{id:`needs-setup`,label:`Needs Setup`},{id:`disabled`,label:`Disabled`}];function _(e,t){switch(t){case`all`:return!0;case`ready`:return!e.disabled&&e.eligible;case`needs-setup`:return!e.disabled&&!e.eligible;case`disabled`:return e.disabled}throw Error(`Unsupported skills status filter`)}function v(e){return e.disabled?`muted`:e.eligible?`ok`:`warn`}function y(e,t){let n=e.clawhub;return!n||n.status!==`linked`||!n.valid?null:t[o({registry:n.registry,slug:n.slug,version:n.installedVersion})]??null}function b(e){if(!e)return`Unavailable`;let t=e.securityStatus?.trim()||null;return e.ok&&e.decision===`pass`?t===`clean`||!t?`Clean`:t:t===`pending`||t===`not-run`?`Pending`:t===`malicious`?`Blocked`:t===`suspicious`?`Review`:`Unavailable`}function x(e){if(!e)return`chip-warn`;if(e.ok&&e.decision===`pass`)return`chip-ok`;let t=e.securityStatus?.trim()||null;return t===`pending`||t===`not-run`?`chip`:`chip-warn`}function S(e){let n=e.report?.skills??[],o={all:n.length,ready:0,"needs-setup":0,disabled:0};for(let e of n)e.disabled?o.disabled++:e.eligible?o.ready++:o[`needs-setup`]++;let s=e.statusFilter===`all`?n:n.filter(t=>_(t,e.statusFilter)),c=a(e.filter),l=c?s.filter(e=>a([e.name,e.description,e.source].join(` `)).includes(c)):s,d=u(l),f=e.detailKey?n.find(t=>t.skillKey===e.detailKey)??null:null;return t`
    <section class="card">
      <div class="row" style="justify-content: space-between;">
        <div>
          <div class="card-title">Skills</div>
          <div class="card-sub">Installed skills and their status.</div>
        </div>
        <button
          class="btn"
          ?disabled=${e.loading||!e.connected}
          @click=${e.onRefresh}
        >
          ${e.loading?i(`common.loading`):i(`common.refresh`)}
        </button>
      </div>

      <div class="agent-tabs" style="margin-top: 14px;">
        ${g.map(n=>t`
            <button
              class="agent-tab ${e.statusFilter===n.id?`active`:``}"
              @click=${()=>e.onStatusFilterChange(n.id)}
            >
              ${n.label}<span class="agent-tab-count">${o[n.id]}</span>
            </button>
          `)}
      </div>

      <div
        class="filters"
        style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 12px;"
      >
        <label class="field" style="flex: 1; min-width: 180px;">
          <input
            .value=${e.filter}
            @input=${t=>e.onFilterChange(t.target.value)}
            placeholder="Filter installed skills"
            autocomplete="off"
            name="skills-filter"
          />
        </label>
        <div class="muted">${l.length} shown</div>
      </div>

      <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 16px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-weight: 600;">ClawHub</div>
          <div class="muted" style="font-size: 13px;">
            Search and install skills from the registry
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
          <label class="field" style="flex: 1; min-width: 180px;">
            <input
              .value=${e.clawhubQuery}
              @input=${t=>e.onClawHubQueryChange(t.target.value)}
              placeholder="Search ClawHub skills…"
              autocomplete="off"
              name="clawhub-search"
            />
          </label>
          ${e.clawhubSearchLoading?t`<span class="muted">Searching…</span>`:r}
        </div>
        ${e.clawhubSearchError?t`<div class="callout danger" style="margin-top: 8px;">
              ${e.clawhubSearchError}
            </div>`:r}
        ${e.clawhubInstallMessage?t`<div
              class="callout ${e.clawhubInstallMessage.kind===`error`?`danger`:`success`}"
              style="margin-top: 8px;"
            >
              ${e.clawhubInstallMessage.text}
            </div>`:r}
        ${C(e)}
      </div>

      ${e.error?t`<div class="callout danger" style="margin-top: 12px;">${e.error}</div>`:r}
      ${l.length===0?t`
            <div class="muted" style="margin-top: 16px">
              ${!e.connected&&!e.report?`Not connected to gateway.`:`No skills found.`}
            </div>
          `:t`
            <div class="agent-skills-groups" style="margin-top: 16px;">
              ${d.map(n=>t`
                  <details class="agent-skills-group" open>
                    <summary class="agent-skills-header">
                      <span>${n.label}</span>
                      <span class="muted">${n.skills.length}</span>
                    </summary>
                    <div class="list skills-grid">
                      ${n.skills.map(t=>T(t,e))}
                    </div>
                  </details>
                `)}
            </div>
          `}
    </section>

    ${f?E(f,e):r}
    ${e.clawhubDetailSlug?w(e):r}
  `}function C(e){let n=e.clawhubResults;return n?n.length===0?t`<div class="muted" style="margin-top: 8px;">No skills found on ClawHub.</div>`:t`
    <div class="list" style="margin-top: 8px;">
      ${n.map(n=>t`
          <div
            class="list-item list-item-clickable"
            @click=${()=>e.onClawHubDetailOpen(n.slug)}
          >
            <div class="list-main">
              <div class="list-title">${n.displayName}</div>
              <div class="list-sub">${n.summary?s(n.summary,120):n.slug}</div>
            </div>
            <div class="list-meta" style="display: flex; align-items: center; gap: 8px;">
              ${n.version?t`<span class="muted" style="font-size: 12px;">v${n.version}</span>`:r}
              <button
                class="btn btn--sm"
                ?disabled=${e.clawhubInstallSlug!==null}
                @click=${t=>{t.stopPropagation(),e.onClawHubInstall(n.slug)}}
              >
                ${e.clawhubInstallSlug===n.slug?`Installing…`:`Install`}
              </button>
            </div>
          </div>
        `)}
    </div>
  `:r}function w(e){let a=e.clawhubDetail;return t`
    <dialog
      class="md-preview-dialog"
      ${n(h)}
      @click=${e=>{let t=e.currentTarget;e.target===t&&t.close()}}
      @close=${e.onClawHubDetailClose}
    >
      <div class="md-preview-dialog__panel">
        <div class="md-preview-dialog__header">
          <div class="md-preview-dialog__title">
            ${a?.skill?.displayName??e.clawhubDetailSlug}
          </div>
          <button
            class="btn btn--sm"
            @click=${e=>{e.currentTarget.closest(`dialog`)?.close()}}
          >
            Close
          </button>
        </div>
        <div class="md-preview-dialog__body" style="display: grid; gap: 16px;">
          ${e.clawhubDetailLoading?t`<div class="muted">${i(`common.loading`)}</div>`:e.clawhubDetailError?t`<div class="callout danger">${e.clawhubDetailError}</div>`:a?.skill?t`
                    <div style="font-size: 14px; line-height: 1.5;">
                      ${a.skill.summary??``}
                    </div>
                    ${a.owner?.displayName?t`<div class="muted" style="font-size: 13px;">
                          By
                          ${a.owner.displayName}${a.owner.handle?t` (@${a.owner.handle})`:r}
                        </div>`:r}
                    ${a.latestVersion?t`<div class="muted" style="font-size: 13px;">
                          Latest: v${a.latestVersion.version}
                        </div>`:r}
                    ${a.latestVersion?.changelog?t`<div
                          style="font-size: 13px; border-top: 1px solid var(--border); padding-top: 12px; white-space: pre-wrap;"
                        >
                          ${a.latestVersion.changelog}
                        </div>`:r}
                    ${a.metadata?.os?t`<div class="muted" style="font-size: 12px;">
                          Platforms: ${a.metadata.os.join(`, `)}
                        </div>`:r}
                    <button
                      class="btn primary"
                      ?disabled=${e.clawhubInstallSlug!==null}
                      @click=${()=>{e.clawhubDetailSlug&&e.onClawHubInstall(e.clawhubDetailSlug)}}
                    >
                      ${e.clawhubInstallSlug===e.clawhubDetailSlug?`Installing…`:`Install ${a.skill.displayName}`}
                    </button>
                  `:t`<div class="muted">Skill not found.</div>`}
        </div>
      </div>
    </dialog>
  `}function T(e,n){let i=n.busyKey===e.skillKey,a=v(e),o=y(e,n.clawhubVerdicts);return t`
    <div class="list-item list-item-clickable" @click=${()=>n.onDetailOpen(e.skillKey)}>
      <div class="list-main">
        <div class="list-title" style="display: flex; align-items: center; gap: 8px;">
          <span class="statusDot ${a}"></span>
          ${e.emoji?t`<span>${e.emoji}</span>`:r}
          <span>${e.name}</span>
        </div>
        <div class="list-sub">${s(e.description,140)}</div>
      </div>
      <div
        class="list-meta"
        style="display: flex; align-items: center; justify-content: flex-end; gap: 10px;"
      >
        ${e.clawhub?.status===`linked`?t`<span class="chip ${x(o)}">${b(o)}</span>`:e.clawhub?.status===`invalid`?t`<span class="chip chip-warn">ClawHub link invalid</span>`:r}
        <label class="skill-toggle-wrap" @click=${e=>e.stopPropagation()}>
          <input
            type="checkbox"
            class="skill-toggle"
            .checked=${!e.disabled}
            ?disabled=${i}
            @change=${t=>{t.stopPropagation(),n.onToggle(e.skillKey,e.disabled)}}
          />
        </label>
      </div>
    </div>
  `}function E(e,i){let a=i.busyKey===e.skillKey,o=i.edits[e.skillKey]??``,s=i.messages[e.skillKey]??null,c=e.install.length>0&&e.missing.bins.length>0,l=!!(e.bundled&&e.source!==`openclaw-bundled`),u=p(e),g=d(e),_=y(e,i.clawhubVerdicts),b=i.detailTab===`card`&&e.skillCard?.present?`card`:`overview`;return t`
    <dialog
      class="md-preview-dialog"
      ${n(h)}
      @click=${e=>{let t=e.currentTarget;e.target===t&&t.close()}}
      @close=${i.onDetailClose}
    >
      <div class="md-preview-dialog__panel">
        <div class="md-preview-dialog__header">
          <div
            class="md-preview-dialog__title"
            style="display: flex; align-items: center; gap: 8px;"
          >
            <span class="statusDot ${v(e)}"></span>
            ${e.emoji?t`<span style="font-size: 18px;">${e.emoji}</span>`:r}
            <span>${e.name}</span>
          </div>
          <button
            class="btn btn--sm"
            @click=${e=>{e.currentTarget.closest(`dialog`)?.close()}}
          >
            Close
          </button>
        </div>
        <div class="md-preview-dialog__body" style="display: grid; gap: 16px;">
          <div>
            <div style="font-size: 14px; line-height: 1.5; color: var(--text);">
              ${e.description}
            </div>
            ${f({skill:e,showBundledBadge:l})}
          </div>

          ${e.clawhub||e.skillCard?.present?t`
                <div class="agent-tabs">
                  <button
                    class="agent-tab ${b===`overview`?`active`:``}"
                    @click=${()=>i.onDetailTabChange(`overview`)}
                  >
                    Overview
                  </button>
                  ${e.skillCard?.present?t`<button
                        class="agent-tab ${b===`card`?`active`:``}"
                        @click=${()=>i.onDetailTabChange(`card`)}
                      >
                        Skill Card
                      </button>`:r}
                </div>
              `:r}
          ${b===`overview`?D(e,i,_):O(e,i)}
          ${u.length>0?t`
                <div
                  class="callout"
                  style="border-color: var(--warn-subtle); background: var(--warn-subtle); color: var(--warn);"
                >
                  <div style="font-weight: 600; margin-bottom: 4px;">Missing requirements</div>
                  <div>${u.join(`, `)}</div>
                </div>
              `:r}
          ${g.length>0?t`
                <div class="muted" style="font-size: 13px;">Reason: ${g.join(`, `)}</div>
              `:r}

          <div style="display: flex; align-items: center; gap: 12px;">
            <label class="skill-toggle-wrap">
              <input
                type="checkbox"
                class="skill-toggle"
                .checked=${!e.disabled}
                ?disabled=${a}
                @change=${()=>i.onToggle(e.skillKey,e.disabled)}
              />
            </label>
            <span style="font-size: 13px; font-weight: 500;">
              ${e.disabled?`Disabled`:`Enabled`}
            </span>
            ${c?t`<button
                  class="btn"
                  ?disabled=${a}
                  @click=${()=>i.onInstall(e.skillKey,e.name,e.install[0].id)}
                >
                  ${a?`Installing…`:e.install[0].label}
                </button>`:r}
          </div>

          ${s?t`<div class="callout ${s.kind===`error`?`danger`:`success`}">
                ${s.message}
              </div>`:r}
          ${e.primaryEnv?t`
                <div style="display: grid; gap: 8px;">
                  <div class="field">
                    <span
                      >API key
                      <span class="muted" style="font-weight: normal; font-size: 0.88em;"
                        >(${e.primaryEnv})</span
                      ></span
                    >
                    <input
                      type="password"
                      .value=${o}
                      @input=${t=>i.onEdit(e.skillKey,t.target.value)}
                    />
                  </div>
                  ${(()=>{let n=m(e.homepage);return n?t`<div class="muted" style="font-size: 13px;">
                          Get your key:
                          <a href="${n}" target="_blank" rel="noopener noreferrer"
                            >${e.homepage}</a
                          >
                        </div>`:r})()}
                  <button
                    class="btn primary"
                    ?disabled=${a}
                    @click=${()=>i.onSaveKey(e.skillKey)}
                  >
                    Save key
                  </button>
                </div>
              `:r}

          <div
            style="border-top: 1px solid var(--border); padding-top: 12px; display: grid; gap: 6px; font-size: 12px; color: var(--muted);"
          >
            <div><span style="font-weight: 600;">Source:</span> ${e.source}</div>
            <div style="font-family: var(--mono); word-break: break-all;">${e.filePath}</div>
            ${(()=>{let n=m(e.homepage);return n?t`<div>
                    <a href="${n}" target="_blank" rel="noopener noreferrer"
                      >${e.homepage}</a
                    >
                  </div>`:r})()}
          </div>
        </div>
      </div>
    </dialog>
  `}function D(e,n,i){let a=e.clawhub;if(!a)return r;if(a.status===`invalid`)return t`<div class="callout danger">
      <div style="font-weight: 600; margin-bottom: 4px;">ClawHub link invalid</div>
      <div>${a.reason}</div>
    </div>`;let o=m(i?.securityAuditUrl??void 0),s=i?.reasons?.length?i.reasons.join(`, `):null;return t`
    <div
      class="callout"
      style="display: grid; gap: 8px; border-color: var(--border); background: var(--panel-2);"
    >
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <span class="chip ${x(i)}">${b(i)}</span>
        <span class="muted" style="font-size: 12px;">${a.slug}@${a.installedVersion}</span>
        ${n.clawhubVerdictsLoading?t`<span class="muted">Refreshing…</span>`:r}
      </div>
      ${n.clawhubVerdictsError?t`<div class="muted" style="font-size: 13px;">${n.clawhubVerdictsError}</div>`:s?t`<div class="muted" style="font-size: 13px;">${s}</div>`:r}
      ${o?t`<div style="font-size: 13px;">
            <a href="${o}" target="_blank" rel="noopener noreferrer"
              >Full security report</a
            >
          </div>`:r}
    </div>
  `}function O(n,i){if(!n.skillCard?.present)return r;let a=i.skillCardContents[n.skillKey];if(a===void 0){let e=i.skillCardErrors[n.skillKey];return e?t`<div class="callout danger">${e}</div>`:t`<div class="muted" style="font-size: 13px;">
      ${i.skillCardLoadingKey===n.skillKey?`Loading Skill Card...`:`Skill Card not loaded.`}
    </div>`}return t`
    <article class="sidebar-markdown" style="max-width: 100%; overflow-wrap: anywhere;">
      ${e(c(a))}
    </article>
  `}export{S as renderSkills};
//# sourceMappingURL=skills-DdjGUIRa.js.map