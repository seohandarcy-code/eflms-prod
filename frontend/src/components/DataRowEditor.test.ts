import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h } from "vue";

vi.mock("../api/admin", () => ({
  fetchDataRows: vi.fn(async () => ({
    ef_code: "EF1",
    table: "",
    key: ["factory_code", "name"],
    columns: [
      { name: "voltage", label: "전압", dtype: "int", na_allowed: false },
      { name: "factory_code", label: "사업장", dtype: "str", choices: ["H1", "K1"], na_allowed: false },
      { name: "name", label: "설비명", dtype: "str", na_allowed: false },
      { name: "grade", label: "등급", dtype: "str", choices: ["A", "B"], na_allowed: true },
    ],
    header: ["voltage", "factory_code", "name", "grade"],
    extra_columns: [],
    rows: [
      ["22900", "H1", "TR1", "A"],
      ["154000", "K1", "TR2", "N/A"],
    ],
  })),
  importPastedData: vi.fn(),
}));

import { importPastedData } from "../api/admin";
import DataRowEditor from "./DataRowEditor.vue";
import { useAuthStore } from "../stores/auth";

async function mountEditor() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: defineComponent({ render: () => h("div") }) }] });
  router.push("/");
  await router.isReady();
  const wrapper = mount(DataRowEditor, { props: { efCode: "EF1", table: "" }, global: { plugins: [router] } });
  await flushPromises();
  return wrapper;
}

describe("DataRowEditor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useAuthStore().$patch({ token: "t" } as never);
    vi.mocked(importPastedData).mockReset();
  });

  it("shows key columns first and locks them on existing rows", async () => {
    const wrapper = await mountEditor();
    const heads = wrapper.findAll("thead th .h-name").map((th) => th.text());
    expect(heads.slice(0, 2)).toEqual(["🔒 factory_code", "🔒 name"]);
    const firstRow = wrapper.findAll("tbody tr")[0];
    expect(firstRow.findAll(".locked").map((el) => el.text())).toEqual(["H1", "TR1"]);
    expect(firstRow.findAll("input").length).toBe(1); // voltage
    expect(firstRow.findAll("select").length).toBe(1); // grade
  });

  it("adds an editable new row and duplicates the selected row", async () => {
    const wrapper = await mountEditor();
    await wrapper.findAll("button").find((b) => b.text() === "+ 행 추가")!.trigger("click");
    let rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(3);
    expect(rows[2].findAll(".locked")).toHaveLength(0);

    await rows[1].find(".no-btn").trigger("click");
    await wrapper.findAll("button").find((b) => b.text() === "선택 행 복제")!.trigger("click");
    rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(4);
    // 새 행이라 🔒 칸도 고칠 수 있다(사업장은 목록, 설비명·전압은 입력칸)
    expect(rows[3].findAll("input").map((el) => (el.element as HTMLInputElement).value)).toEqual(["TR2", "154000"]);
    expect(wrapper.emitted("dirty")!.at(-1)).toEqual([1]); // 복제한 행만(빈 새 행은 안 보냄)
  });

  it("sends only changed rows for checking and maps errors back to cells", async () => {
    vi.mocked(importPastedData).mockResolvedValue({
      kind: "equipment",
      ok: false,
      dry_run: true,
      file_errors: [],
      row_errors: [{ row_number: 2, column: "voltage", raw_value: "x", reason: "정수가 아님" }],
      row_actions: [],
    } as never);
    const wrapper = await mountEditor();
    const input = wrapper.findAll("tbody tr")[1].find("input");
    await input.setValue("x");
    await wrapper.findAll("button").find((b) => b.text().startsWith("변경 검증"))!.trigger("click");
    await flushPromises();

    const call = vi.mocked(importPastedData).mock.calls[0][1];
    expect(call).toMatchObject({ efCode: "EF1", table: "", replace: false, check: true });
    expect(call.text).toBe("voltage\tfactory_code\tname\tgrade\nx\tK1\tTR2\tN/A\n");
    const cell = wrapper.find("td.cell-error");
    expect(cell.attributes("title")).toBe("정수가 아님");
    expect(wrapper.text()).toContain("오류 1건");
  });
});
