# This method is taken from pdfminer.six [20240706] pdfminer/utils.py
# in order to break its connection with pdfminer.six sources
# UnsupportedException is imported as PDFValueError

from pdfsh.exceptions import NotSupportedException as PdfValueError


def apply_png_predictor(
    pred: int, colors: int, columns: int, bitspercomponent: int, data: bytes
) -> bytes:
    """Reverse the effect of the PNG predictor

    Documentation: http://www.libpng.org/pub/png/spec/1.2/PNG-Filters.html
    """
    if bitspercomponent not in [8, 1]:
        msg = "Unsupported `bitspercomponent': %d" % bitspercomponent
        raise PDFValueError(msg)

    nbytes = colors * columns * bitspercomponent // 8
    bpp = colors * bitspercomponent // 8  # number of bytes per complete pixel
    buf = []
    line_above = list(b"\x00" * columns)
    for scanline_i in range(0, len(data), nbytes + 1):
        filter_type = data[scanline_i]
        line_encoded = data[scanline_i + 1 : scanline_i + 1 + nbytes]
        raw = []

        if filter_type == 0:
            # Filter type 0: None
            raw = list(line_encoded)

        elif filter_type == 1:
            # Filter type 1: Sub
            # To reverse the effect of the Sub() filter after decompression,
            # output the following value:
            #   Raw(x) = Sub(x) + Raw(x - bpp)
            # (computed mod 256), where Raw() refers to the bytes already
            #  decoded.
            for j, sub_x in enumerate(line_encoded):
                if j - bpp < 0:
                    raw_x_bpp = 0
                else:
                    raw_x_bpp = int(raw[j - bpp])
                raw_x = (sub_x + raw_x_bpp) & 255
                raw.append(raw_x)

        elif filter_type == 2:
            # Filter type 2: Up
            # To reverse the effect of the Up() filter after decompression,
            # output the following value:
            #   Raw(x) = Up(x) + Prior(x)
            # (computed mod 256), where Prior() refers to the decoded bytes of
            # the prior scanline.
            for up_x, prior_x in zip(line_encoded, line_above):
                raw_x = (up_x + prior_x) & 255
                raw.append(raw_x)

        elif filter_type == 3:
            # Filter type 3: Average
            # To reverse the effect of the Average() filter after
            # decompression, output the following value:
            #    Raw(x) = Average(x) + floor((Raw(x-bpp)+Prior(x))/2)
            # where the result is computed mod 256, but the prediction is
            # calculated in the same way as for encoding. Raw() refers to the
            # bytes already decoded, and Prior() refers to the decoded bytes of
            # the prior scanline.
            for j, average_x in enumerate(line_encoded):
                if j - bpp < 0:
                    raw_x_bpp = 0
                else:
                    raw_x_bpp = int(raw[j - bpp])
                prior_x = int(line_above[j])
                raw_x = (average_x + (raw_x_bpp + prior_x) // 2) & 255
                raw.append(raw_x)

        elif filter_type == 4:
            # Filter type 4: Paeth
            # To reverse the effect of the Paeth() filter after decompression,
            # output the following value:
            #    Raw(x) = Paeth(x)
            #             + PaethPredictor(Raw(x-bpp), Prior(x), Prior(x-bpp))
            # (computed mod 256), where Raw() and Prior() refer to bytes
            # already decoded. Exactly the same PaethPredictor() function is
            # used by both encoder and decoder.
            for j, paeth_x in enumerate(line_encoded):
                if j - bpp < 0:
                    raw_x_bpp = 0
                    prior_x_bpp = 0
                else:
                    raw_x_bpp = int(raw[j - bpp])
                    prior_x_bpp = int(line_above[j - bpp])
                prior_x = int(line_above[j])
                paeth = paeth_predictor(raw_x_bpp, prior_x, prior_x_bpp)
                raw_x = (paeth_x + paeth) & 255
                raw.append(raw_x)

        else:
            raise PDFValueError("Unsupported predictor value: %d" % filter_type)

        buf.extend(raw)
        line_above = raw
    return bytes(buf)
