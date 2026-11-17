import { describe, expect, it } from "vitest";
import { decodeFileBytes, errorKey, parsePasted } from "./pasteData";

describe("pasteData (Stage 16-6)", () => {
  it("엑셀 붙여넣기(CRLF·따옴표·끝 빈 줄)를 헤더와 행으로 나눈다", () => {
    const t = parsePasted('"year"\t"gamma_y"\r\n1\t3.57\r\n2\t"3,24"\r\n\r\n');
    expect(t.header).toEqual(["year", "gamma_y"]);
    expect(t.rows).toEqual([
      { rowNumber: 2, cells: ["1", "3.57"] },
      { rowNumber: 3, cells: ["2", "3,24"] },
    ]);
  });

  it("빈 줄은 건너뛰되 줄 번호는 실제 줄 기준(서버 오류 row_number와 맞춤)", () => {
    const t = parsePasted("\nh1\th2\n\na\tb\n\n\nc\td");
    expect(t.header).toEqual(["h1", "h2"]);
    expect(t.rows.map((r) => r.rowNumber)).toEqual([4, 7]);
  });

  it("BOM 제거, 빈 내용, 따옴표 안의 큰따옴표", () => {
    expect(parsePasted("﻿a\tb\n1\t2").header).toEqual(["a", "b"]);
    expect(parsePasted("  \n\t\n")).toEqual({ header: [], rows: [] });
    expect(parsePasted('a\n"say ""hi"""').rows[0].cells).toEqual(['say "hi"']);
  });

  it("파일 바이트: UTF-8(BOM) 우선, 아니면 CP949", () => {
    const utf8 = new TextEncoder().encode("﻿사업장\tA");
    expect(decodeFileBytes(utf8.buffer as ArrayBuffer)).toBe("사업장\tA");
    // "가" in CP949 = 0xB0 0xA1 (UTF-8로는 잘못된 바이트)
    const cp949 = new Uint8Array([0xb0, 0xa1]);
    expect(decodeFileBytes(cp949.buffer)).toBe("가");
  });

  it("오류 칸 키", () => {
    expect(errorKey(3, "con_rank")).toBe("3|con_rank");
  });
});
