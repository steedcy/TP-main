package com.airport.ai.devicetype;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 五类设备类型 x 八类能力约束矩阵的最小 .xlsx 导出（DEF-S3-018、TC-017.S3）。
 * 只用 java.util.zip 写出 SpreadsheetML，不引入新依赖；单元格内容为共享字符串，支持 Excel 直接打开。
 */
public final class CapabilityMatrixXlsx {

    private CapabilityMatrixXlsx() {}

    public static final String SUPPORTED = "支持";
    public static final String UNSUPPORTED = "不支持";

    /** rows: 每行第一列设备类型编码、第二列名称，其后依次对应 capabilityHeaders。 */
    public static byte[] build(List<String> capabilityHeaders, List<List<String>> rows) {
        try (ByteArrayOutputStream bytes = new ByteArrayOutputStream();
             ZipOutputStream zip = new ZipOutputStream(bytes, StandardCharsets.UTF_8)) {
            put(zip, "[Content_Types].xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                    <Default Extension="xml" ContentType="application/xml"/>
                    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
                    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
                    </Types>""");
            put(zip, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
                    </Relationships>""");
            put(zip, "xl/workbook.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                    <sheets><sheet name="能力约束矩阵" sheetId="1" r:id="rId1"/></sheets>
                    </workbook>""");
            put(zip, "xl/_rels/workbook.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
                    </Relationships>""");
            StringBuilder sheet = new StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>");
            List<String> header = new java.util.ArrayList<>(List.of("设备类型编码", "设备类型名称"));
            header.addAll(capabilityHeaders);
            row(sheet, 1, header);
            int r = 2;
            for (List<String> cells : rows) row(sheet, r++, cells);
            sheet.append("</sheetData></worksheet>");
            put(zip, "xl/worksheets/sheet1.xml", sheet.toString());
            zip.finish();
            return bytes.toByteArray();
        } catch (IOException e) {
            throw new IllegalStateException("生成矩阵Excel失败", e);
        }
    }

    private static void row(StringBuilder sb, int rowNumber, List<String> cells) {
        sb.append("<row r=\"").append(rowNumber).append("\">");
        for (int c = 0; c < cells.size(); c++) {
            sb.append("<c r=\"").append((char) ('A' + c)).append(rowNumber).append("\" t=\"inlineStr\"><is><t>")
                    .append(escape(cells.get(c))).append("</t></is></c>");
        }
        sb.append("</row>");
    }

    private static String escape(String s) {
        return s == null ? "" : s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private static void put(ZipOutputStream zip, String name, String content) throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        zip.write(content.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }
}
