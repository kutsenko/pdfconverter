"""Tests for PDF type detection and optimization selection."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.converter import (
    PdfType,
    _count_pdf_images,
    _is_full_page_image_pdf,
    _detect_pdf_type,
)


class TestPdfImageCounting:
    """Tests for _count_pdf_images function."""

    @patch("app.converter.pikepdf.open")
    def test_count_images_no_images(self, mock_open):
        """Test counting images in PDF with no images."""
        # Arrange
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.__contains__ = Mock(return_value=False)  # No /Resources
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == 0

    @patch("app.converter.pikepdf.open")
    def test_count_images_with_single_image(self, mock_open):
        """Test counting images in PDF with one image."""
        # Arrange
        mock_pdf = Mock()
        mock_page = Mock()

        # Mock XObject with one image
        mock_image = Mock()
        mock_image.__contains__ = Mock(return_value=True)
        mock_image.Subtype = "/Image"

        mock_xobjects = Mock()
        mock_xobjects.__iter__ = Mock(return_value=iter(["/Im0"]))
        mock_xobjects.__getitem__ = Mock(return_value=mock_image)

        mock_resources = Mock()
        mock_resources.XObject = mock_xobjects

        mock_page.__contains__ = Mock(side_effect=lambda x: x in ["/Resources"])
        mock_page.Resources = mock_resources
        mock_page.Resources.__contains__ = Mock(return_value=True)

        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == 1

    @patch("app.converter.pikepdf.open")
    def test_count_images_multiple_pages_multiple_images(self, mock_open):
        """Test counting images across multiple pages."""
        # Arrange
        mock_pdf = Mock()

        # Create 3 pages with 2, 1, 0 images respectively
        mock_page1 = self._create_mock_page_with_images(2)
        mock_page2 = self._create_mock_page_with_images(1)
        mock_page3 = self._create_mock_page_with_images(0)

        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == 3

    @patch("app.converter.pikepdf.open")
    def test_count_images_error_handling(self, mock_open):
        """Test that errors during image counting are handled gracefully."""
        # Arrange
        mock_open.side_effect = Exception("PDF open failed")

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == -1  # Error indicator

    @patch("app.converter.pikepdf.open")
    def test_count_images_page_without_resources(self, mock_open):
        """Test counting images when page has no Resources."""
        # Arrange
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.__contains__ = Mock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == 0

    @patch("app.converter.pikepdf.open")
    def test_count_images_resources_without_xobject(self, mock_open):
        """Test counting images when Resources has no XObject."""
        # Arrange
        mock_pdf = Mock()
        mock_page = Mock()
        mock_resources = Mock()
        mock_resources.__contains__ = Mock(return_value=False)  # No /XObject

        mock_page.__contains__ = Mock(side_effect=lambda x: x == "/Resources")
        mock_page.Resources = mock_resources

        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == 0

    @patch("app.converter.pikepdf.open")
    def test_count_images_xobject_is_not_image(self, mock_open):
        """Test counting images when XObject is not an Image (e.g., Form)."""
        # Arrange
        mock_pdf = Mock()
        mock_page = Mock()

        # Mock XObject with a Form (not an image)
        mock_form = Mock()
        mock_form.__contains__ = Mock(return_value=True)
        mock_form.Subtype = "/Form"  # Not an image

        mock_xobjects = Mock()
        mock_xobjects.__iter__ = Mock(return_value=iter(["/Fm0"]))
        mock_xobjects.__getitem__ = Mock(return_value=mock_form)

        mock_resources = Mock()
        mock_resources.XObject = mock_xobjects
        mock_resources.__contains__ = Mock(return_value=True)

        mock_page.__contains__ = Mock(side_effect=lambda x: x == "/Resources")
        mock_page.Resources = mock_resources

        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        count = _count_pdf_images(Path("/tmp/test.pdf"))

        # Assert
        assert count == 0

    def _create_mock_page_with_images(self, num_images):
        """Helper to create mock page with specified number of images."""
        mock_page = Mock()

        if num_images == 0:
            mock_page.__contains__ = Mock(return_value=False)
            return mock_page

        # Create mock images
        mock_images = []
        image_names = []
        for i in range(num_images):
            mock_image = Mock()
            mock_image.__contains__ = Mock(return_value=True)
            mock_image.Subtype = "/Image"
            mock_images.append(mock_image)
            image_names.append(f"/Im{i}")

        mock_xobjects = Mock()
        mock_xobjects.__iter__ = Mock(return_value=iter(image_names))
        mock_xobjects.__getitem__ = Mock(
            side_effect=lambda name: mock_images[int(name[3:])]
        )

        mock_resources = Mock()
        mock_resources.XObject = mock_xobjects
        mock_resources.__contains__ = Mock(return_value=True)

        mock_page.__contains__ = Mock(side_effect=lambda x: x == "/Resources")
        mock_page.Resources = mock_resources

        return mock_page


class TestFullPageImageDetection:
    """Tests for _is_full_page_image_pdf function."""

    @patch("app.converter.pikepdf.open")
    def test_single_page_single_image_is_full_page(self, mock_open):
        """Test that single page with single image is detected as full-page scan."""
        # Arrange
        mock_pdf = Mock()
        mock_page = self._create_mock_page_with_n_images(1)
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is True

    @patch("app.converter.pikepdf.open")
    def test_multiple_pages_all_single_images(self, mock_open):
        """Test multi-page PDF where all pages have single images."""
        # Arrange
        mock_pdf = Mock()
        mock_pdf.pages = [
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
        ]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is True

    @patch("app.converter.pikepdf.open")
    def test_mixed_pages_below_threshold(self, mock_open):
        """Test that mixed content below 80% threshold is not classified as scanned."""
        # Arrange - 50% single-image pages (below 80% threshold)
        mock_pdf = Mock()
        mock_pdf.pages = [
            self._create_mock_page_with_n_images(1),  # Full page
            self._create_mock_page_with_n_images(3),  # Multiple images
        ]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is False

    @patch("app.converter.pikepdf.open")
    def test_threshold_boundary_exactly_80_percent(self, mock_open):
        """Test that exactly 80% single-image pages is not full-page (>80% required)."""
        # Arrange - Exactly 80% (4 out of 5 pages)
        mock_pdf = Mock()
        mock_pdf.pages = [
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(2),  # Not single image
        ]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is False  # Exactly 80% is not > 80%

    @patch("app.converter.pikepdf.open")
    def test_threshold_boundary_above_80_percent(self, mock_open):
        """Test that >80% single-image pages is classified as full-page."""
        # Arrange - 90% (9 out of 10 pages)
        mock_pdf = Mock()
        mock_pdf.pages = [
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(1),
            self._create_mock_page_with_n_images(2),  # Not single image
        ]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is True

    @patch("app.converter.pikepdf.open")
    def test_no_images_not_full_page(self, mock_open):
        """Test that PDF with no images is not classified as scanned."""
        # Arrange
        mock_pdf = Mock()
        mock_page = self._create_mock_page_with_n_images(0)
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is False

    @patch("app.converter.pikepdf.open")
    def test_empty_pdf_not_full_page(self, mock_open):
        """Test that empty PDF (no pages) is not classified as scanned."""
        # Arrange
        mock_pdf = Mock()
        mock_pdf.pages = []
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is False

    @patch("app.converter.pikepdf.open")
    def test_error_handling(self, mock_open):
        """Test that errors during detection are handled gracefully."""
        # Arrange
        mock_open.side_effect = Exception("PDF open failed")

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is False

    @patch("app.converter.pikepdf.open")
    def test_page_with_multiple_images(self, mock_open):
        """Test that pages with multiple images are not counted as full-page."""
        # Arrange
        mock_pdf = Mock()
        mock_pdf.pages = [
            self._create_mock_page_with_n_images(3),  # Multiple images
        ]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_pdf

        # Act
        is_full_page = _is_full_page_image_pdf(Path("/tmp/test.pdf"))

        # Assert
        assert is_full_page is False

    def _create_mock_page_with_n_images(self, n):
        """Helper to create a mock page with n images."""
        mock_page = Mock()

        if n == 0:
            mock_page.__contains__ = Mock(return_value=False)
            return mock_page

        # Create n mock images
        image_names = [f"/Im{i}" for i in range(n)]
        mock_images = {}
        for name in image_names:
            img = Mock()
            img.__contains__ = Mock(return_value=True)
            img.Subtype = "/Image"
            mock_images[name] = img

        mock_xobjects = Mock()
        mock_xobjects.__iter__ = Mock(return_value=iter(image_names))
        mock_xobjects.__getitem__ = Mock(side_effect=lambda name: mock_images[name])

        mock_resources = Mock()
        mock_resources.XObject = mock_xobjects
        mock_resources.__contains__ = Mock(return_value=True)

        mock_page.__contains__ = Mock(side_effect=lambda x: x == "/Resources")
        mock_page.Resources = mock_resources

        return mock_page


class TestPdfTypeDetection:
    """Tests for _detect_pdf_type function."""

    @patch("app.converter._is_full_page_image_pdf")
    @patch("app.converter._count_pdf_images")
    def test_detect_text_only_pdf(self, mock_count, mock_full_page):
        """Test detection of text-only PDF."""
        # Arrange
        mock_count.return_value = 0

        # Act
        pdf_type = _detect_pdf_type(Path("/tmp/test.pdf"))

        # Assert
        assert pdf_type == PdfType.TEXT_ONLY
        mock_full_page.assert_not_called()

    @patch("app.converter._is_full_page_image_pdf")
    @patch("app.converter._count_pdf_images")
    def test_detect_scanned_image_pdf(self, mock_count, mock_full_page):
        """Test detection of scanned image PDF."""
        # Arrange
        mock_count.return_value = 5
        mock_full_page.return_value = True

        # Act
        pdf_type = _detect_pdf_type(Path("/tmp/test.pdf"))

        # Assert
        assert pdf_type == PdfType.SCANNED_IMAGE

    @patch("app.converter._is_full_page_image_pdf")
    @patch("app.converter._count_pdf_images")
    def test_detect_mixed_content_pdf(self, mock_count, mock_full_page):
        """Test detection of mixed content PDF."""
        # Arrange
        mock_count.return_value = 3
        mock_full_page.return_value = False

        # Act
        pdf_type = _detect_pdf_type(Path("/tmp/test.pdf"))

        # Assert
        assert pdf_type == PdfType.MIXED_CONTENT

    @patch("app.converter._count_pdf_images")
    def test_detect_unknown_on_error(self, mock_count):
        """Test that detection failures return UNKNOWN type."""
        # Arrange
        mock_count.return_value = -1  # Error indicator

        # Act
        pdf_type = _detect_pdf_type(Path("/tmp/test.pdf"))

        # Assert
        assert pdf_type == PdfType.UNKNOWN

    @patch("app.converter._count_pdf_images")
    def test_detect_handles_exceptions(self, mock_count):
        """Test that exceptions during detection are caught."""
        # Arrange
        mock_count.side_effect = Exception("Detection error")

        # Act
        pdf_type = _detect_pdf_type(Path("/tmp/test.pdf"))

        # Assert
        assert pdf_type == PdfType.UNKNOWN

    @patch("app.converter._is_full_page_image_pdf")
    @patch("app.converter._count_pdf_images")
    def test_detect_single_image_not_full_page(self, mock_count, mock_full_page):
        """Test PDF with one image but not full-page layout is mixed content."""
        # Arrange
        mock_count.return_value = 1
        mock_full_page.return_value = False

        # Act
        pdf_type = _detect_pdf_type(Path("/tmp/test.pdf"))

        # Assert
        assert pdf_type == PdfType.MIXED_CONTENT
