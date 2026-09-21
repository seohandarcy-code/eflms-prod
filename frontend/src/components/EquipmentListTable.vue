<script setup lang="ts">
import type { EquipmentSummary } from "../types/equipment";
import { statusBg, statusColor, statusLabel } from "../utils/statusStyle";

defineProps<{ items: EquipmentSummary[]; activeId: number | null }>();
const emit = defineEmits<{ select: [equipmentId: number] }>();
</script>

<template>
  <table class="equipment-table">
    <thead>
      <tr>
        <th>설비명</th>
        <th>사업장</th>
        <th>전압</th>
        <th class="num">POF</th>
        <th class="num">COF</th>
        <th class="num">DOF</th>
        <th class="num">종합점수</th>
        <th>상태</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="item in items"
        :key="item.equipment_id"
        class="row"
        :class="{ active: activeId === item.equipment_id }"
        :style="activeId === item.equipment_id ? { borderLeftColor: statusColor(item.status) } : {}"
        @click="emit('select', item.equipment_id)"
      >
        <td class="name">{{ item.transformer_name }}</td>
        <td>{{ item.factory_code }}</td>
        <td>{{ item.voltage.toLocaleString() }}V</td>
        <td class="num mono">{{ item.pof }}</td>
        <td class="num mono">{{ item.cof }}</td>
        <td class="num mono">{{ item.dof }}</td>
        <td class="num mono score">{{ item.total_score.toFixed(1) }}</td>
        <td>
          <span class="chip" :style="{ background: statusBg(item.status), color: statusColor(item.status) }">
            {{ statusLabel(item.status) }}
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.equipment-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  overflow: hidden;
  font: 500 13px "IBM Plex Sans", sans-serif;
}
thead {
  background: #f4f5f7;
}
th {
  text-align: left;
  padding: 10px 14px;
  font: 600 11px "IBM Plex Sans", sans-serif;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #8891a0;
  border-bottom: 1px solid #e2e5ea;
}
th.num {
  text-align: right;
}
.row {
  cursor: pointer;
  border-left: 3px solid transparent;
}
.row:hover {
  background: #f9fafb;
}
.row.active {
  background: #fafbfc;
  font-weight: 600;
}
td {
  padding: 9px 14px;
  border-bottom: 1px solid #eef0f3;
  color: #4a5361;
}
.name {
  font-weight: 700;
  color: #1a2230;
}
.num {
  text-align: right;
}
.mono {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.score {
  color: #1a2230;
  font-weight: 700;
}
.chip {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
</style>
