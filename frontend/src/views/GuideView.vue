<script setup lang="ts">
import { computed } from "vue";
import { COF_FIELD_LABELS, DOF_FIELD_LABELS, POF_FIELD_LABELS } from "../utils/scoreBreakdown";
import { statusColor, statusLabel } from "../utils/statusStyle";

const pofItems = computed(() => Object.values(POF_FIELD_LABELS));
const cofItems = computed(() => Object.values(COF_FIELD_LABELS));
const dofItems = computed(() => Object.values(DOF_FIELD_LABELS));
</script>

<template>
  <div class="guide">
    <header class="topbar">
      <div class="brand">
        <div class="brand-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
        </div>
        <div>
          <div class="title">POF · COF · DOF 지표 설명</div>
          <div class="subtitle">설비 건전성 점수가 어떻게 매겨지는지 정리한 안내 페이지입니다.</div>
        </div>
      </div>
      <RouterLink to="/" class="back-link">← 대시보드로</RouterLink>
    </header>

    <main class="body">
      <section class="card">
        <h2>세 가지 평가 축</h2>
        <p class="lead">EFLMS는 설비 하나마다 세 가지 축으로 건전성을 평가합니다. 각 축은 0~100점 사이의 값을 가지며, 100에서 감점 항목들을 뺀 값입니다.</p>
        <div class="axis-cards">
          <div class="axis-card">
            <div class="axis-name">POF</div>
            <div class="axis-full">고장확률 (Probability of Failure)</div>
            <p>설비 자체의 상태·진단 결과를 바탕으로, 이 설비가 실제로 고장날 가능성이 얼마나 되는지를 나타냅니다. DGA(유중가스), Furan, 부분방전, 절연내력 시험 등 정기 진단 결과가 반영됩니다.</p>
          </div>
          <div class="axis-card">
            <div class="axis-name">COF</div>
            <div class="axis-full">고장영향 (Consequence of Failure)</div>
            <p>이 설비가 실제로 고장 났을 때 파급되는 영향의 크기입니다. 전압·용량이 클수록, 화재 확산 위험이 크거나 비상대응·교체에 시간과 비용이 많이 들수록 영향이 큰 것으로 평가됩니다.</p>
          </div>
          <div class="axis-card">
            <div class="axis-name">DOF</div>
            <div class="axis-full">설계/방어수준 (Degree of Failure protection)</div>
            <p>고장이 나더라도 피해를 줄여줄 예비 설비·보호 장치가 얼마나 갖춰져 있는지입니다. 예비화, 계통자동전환, 온라인 유중가스 감시, 안전공사 정밀점검 이력 등이 반영됩니다.</p>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>종합점수 계산</h2>
        <p class="lead">세 축의 감점을 아래 비율로 합산해 종합점수를 만듭니다 — POF의 비중이 가장 크고, DOF가 가장 작습니다.</p>
        <div class="formula">종합점수 = 0.5 × POF 감점 + 0.3 × COF 감점 + 0.2 × DOF 감점</div>
      </section>

      <section class="card">
        <h2>각 축을 구성하는 항목</h2>
        <p class="lead">아래 항목들에서 기준 미달이 있으면 해당 축에서 감점됩니다(대시보드의 "점검필요 순위" 패널에서 항목에 마우스를 올리면 이 설비의 실제 측정값을 볼 수 있습니다).</p>
        <div class="axis-cards">
          <div class="axis-card">
            <div class="axis-name">POF 구성 항목</div>
            <ul>
              <li v-for="label in pofItems" :key="label">{{ label }}</li>
            </ul>
          </div>
          <div class="axis-card">
            <div class="axis-name">COF 구성 항목</div>
            <ul>
              <li v-for="label in cofItems" :key="label">{{ label }}</li>
            </ul>
          </div>
          <div class="axis-card">
            <div class="axis-name">DOF 구성 항목</div>
            <ul>
              <li v-for="label in dofItems" :key="label">{{ label }}</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>정상 / 교체검토 / 즉시교체 판정 기준</h2>
        <p class="lead">
          COF·DOF가 둘 다 60을 넘으면(다른 방어 수단이 충분하면) POF 기준이 완화되고, 그렇지 않으면 더 엄격한 기준이 적용됩니다.
        </p>
        <table class="rule-table">
          <thead>
            <tr>
              <th>조건</th>
              <th :style="{ color: statusColor('normal') }">{{ statusLabel("normal") }}</th>
              <th :style="{ color: statusColor('review') }">{{ statusLabel("review") }}</th>
              <th :style="{ color: statusColor('replace') }">{{ statusLabel("replace") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>COF &gt; 60 <b>그리고</b> DOF &gt; 60</td>
              <td>POF &gt; 50</td>
              <td>30 ≤ POF ≤ 50</td>
              <td>POF &lt; 30</td>
            </tr>
            <tr>
              <td>COF ≤ 60 <b>또는</b> DOF ≤ 60</td>
              <td>POF &gt; 60</td>
              <td>40 ≤ POF ≤ 60</td>
              <td>POF &lt; 40</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>

<style scoped>
.guide {
  min-height: 100vh;
  background: #f4f5f7;
  font-family: "IBM Plex Sans", system-ui, sans-serif;
  color: #1a2230;
}
.topbar {
  background: #fff;
  border-bottom: 1px solid #e2e5ea;
  padding: 24px 32px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.brand-icon {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: #0f8a8a;
  display: flex;
  align-items: center;
  justify-content: center;
}
.title {
  font-size: 24px;
  font-weight: 700;
}
.subtitle {
  font-size: 14px;
  color: #8891a0;
  margin-top: 4px;
}
.back-link {
  font-size: 13px;
  font-weight: 600;
  color: #4a5361;
  text-decoration: none;
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 7px 14px;
  white-space: nowrap;
}
.back-link:hover {
  background: #f4f5f7;
}
.body {
  max-width: 880px;
  margin: 0 auto;
  padding: 32px 24px 60px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.card {
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 10px;
  padding: 24px 28px;
}
h2 {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 8px;
}
.lead {
  font-size: 13px;
  color: #4a5361;
  line-height: 1.6;
  margin: 0 0 16px;
}
.axis-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.axis-card {
  background: #f9fafb;
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 16px;
}
.axis-name {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 2px;
}
.axis-full {
  font-size: 12px;
  color: #8891a0;
  margin-bottom: 8px;
}
.axis-card p {
  font-size: 12px;
  color: #4a5361;
  line-height: 1.6;
  margin: 0;
}
.axis-card ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #4a5361;
  line-height: 1.8;
}
.formula {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 14px;
  font-weight: 600;
  background: #f9fafb;
  border: 1px solid #eef0f3;
  border-radius: 8px;
  padding: 14px 18px;
}
.rule-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.rule-table th,
.rule-table td {
  border: 1px solid #eef0f3;
  padding: 10px 12px;
  text-align: left;
}
.rule-table th {
  background: #f9fafb;
  font-weight: 700;
}
</style>
