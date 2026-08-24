import PptxGenJS from "pptxgenjs";
import { toPng } from "html-to-image";
import { toast } from "sonner";
import { formatDate } from "./dateFormatter";

export const createPPT = (title: string) => {
  const pptx = new PptxGenJS();
  pptx.layout = "LAYOUT_WIDE";
  pptx.title = title;

  // Define Master Slide
  pptx.defineSlideMaster({
    title: "MASTER_SLIDE",
    background: { color: "FFFFFF" },
    objects: [
      {
        rect: { x: 0, y: 0, w: "100%", h: 0.8, fill: { color: "1E3A8A" } },
      },
      {
        text: {
          text: title,
          options: { x: 0.3, y: 0.1, w: 10, h: 0.6, fontSize: 18, color: "FFFFFF", bold: true, valign: "middle" }
        }
      },
      {
        text: {
          text: `Generated on ${formatDate(new Date())}`,
          options: { x: 9.5, y: 0.1, w: 3.5, h: 0.6, fontSize: 12, color: "FFFFFF", align: "right", valign: "middle" }
        }
      },
      {
        text: {
          text: "Page ",
          options: { x: 12.0, y: 7.1, w: 1, h: 0.3, fontSize: 10, color: "666666", align: "right" }
        }
      }
    ],
    slideNumber: { x: 13.0, y: 7.1, color: "666666", fontSize: 10 }
  });

  return pptx;
};

export const addTableSlide = (pptx: PptxGenJS, title: string, headers: string[], rows: any[][]) => {
  try {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    
    slide.addText(title, {
      x: 0.5, y: 1.0, w: "90%", h: 0.5, fontSize: 16, bold: true, color: "333333"
    });

    if (rows.length === 0) {
      slide.addText("No data available.", {
        x: 0.5, y: 2.0, w: "90%", h: 0.5, fontSize: 12, color: "666666"
      });
      return;
    }

    const tableData = [
      headers.map(h => ({ text: h, options: { fill: { color: "F3F4F6" }, bold: true, color: "333333", border: { pt: 1, color: "CCCCCC" } } })),
      ...rows.map(row => row.map(cell => ({ text: String(cell ?? ""), options: { border: { pt: 1, color: "EEEEEE" }, fontSize: 10 } })))
    ];

    slide.addTable(tableData, {
      x: 0.5,
      y: 1.7,
      w: 12.33,
      colW: headers.map(() => 12.33 / headers.length),
      autoPage: true,
      autoPageRepeatHeader: true,
      autoPageSlideStartY: 1.7,
      margin: 0.1,
      fontSize: 10
    });
  } catch (err) {
    console.error("Error in addTableSlide:", err);
  }
};

export const addImageSlide = async (pptx: PptxGenJS, title: string, elementId: string) => {
  const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
  slide.addText(title, {
    x: 0.5, y: 1.0, w: "90%", h: 0.5, fontSize: 16, bold: true, color: "333333"
  });

  const el = document.getElementById(elementId);
  if (!el) {
    console.warn(`Element with ID ${elementId} not found.`);
    slide.addText("Section not found.", { x: 0.5, y: 2.0, w: "90%", h: 0.5, fontSize: 12, color: "666666" });
    return;
  }

  try {
    const dataUrl = await toPng(el, { 
      pixelRatio: 3, 
      backgroundColor: "#ffffff",
      skipFonts: false
    });

    slide.addImage({
      data: dataUrl,
      x: 0.5,
      y: 1.7,
      w: 12.33,
      h: 5.5,
      sizing: { type: "contain", w: 12.33, h: 5.5 }
    });
  } catch (err: any) {
    console.error("Error capturing element:", err);
    toast.error(`Error capturing screenshot for ${title}: ` + (err.message || err.toString()));
    slide.addText("Content could not be captured.", { x: 0.5, y: 2.0, w: "90%", h: 0.5, fontSize: 12, color: "666666" });
  }
};
