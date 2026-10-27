Add-Type -AssemblyName System.Drawing

$iconsDirectory = Join-Path $PSScriptRoot "../icons"
New-Item -ItemType Directory -Force -Path $iconsDirectory | Out-Null

function New-RoundedTilePath([float]$x, [float]$y, [float]$width, [float]$height, [float]$radius) {
  $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
  $diameter = $radius * 2
  $path.AddArc($x, $y, $diameter, $diameter, 180, 90)
  $path.AddArc($x + $width - $diameter, $y, $diameter, $diameter, 270, 90)
  $path.AddArc($x + $width - $diameter, $y + $height - $diameter, $diameter, $diameter, 0, 90)
  $path.AddArc($x, $y + $height - $diameter, $diameter, $diameter, 90, 90)
  $path.CloseFigure()
  return $path
}

foreach ($size in @(16, 32, 48, 128)) {
  $bitmap = [System.Drawing.Bitmap]::new(
    $size,
    $size,
    [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
  )
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $graphics.Clear([System.Drawing.Color]::Transparent)

  $margin = $size * 0.035
  $radius = $size * 0.24
  $tile = New-RoundedTilePath $margin $margin ($size - 2 * $margin) ($size - 2 * $margin) $radius
  $navy = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(22, 61, 80))
  $white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
  $orange = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(241, 125, 55))
  $graphics.FillPath($navy, $tile)

  $font = [System.Drawing.Font]::new(
    "Segoe UI",
    ($size * 0.55),
    [System.Drawing.FontStyle]::Bold,
    [System.Drawing.GraphicsUnit]::Pixel
  )
  $format = [System.Drawing.StringFormat]::new()
  $format.Alignment = [System.Drawing.StringAlignment]::Center
  $format.LineAlignment = [System.Drawing.StringAlignment]::Center
  $letterArea = [System.Drawing.RectangleF]::new($size * 0.02, $size * 0.015, $size * 0.85, $size * 0.91)
  $graphics.DrawString("A", $font, $white, $letterArea, $format)

  $lensSize = $size * 0.28
  $lensX = $size * 0.62
  $lensY = $size * 0.61
  $graphics.FillEllipse($orange, $lensX, $lensY, $lensSize, $lensSize)
  $ring = [System.Drawing.Pen]::new(
    [System.Drawing.Color]::White,
    [Math]::Max(1.0, $size * 0.045)
  )
  $graphics.DrawEllipse($ring, $lensX + $lensSize * 0.18, $lensY + $lensSize * 0.15, $lensSize * 0.5, $lensSize * 0.5)
  $ring.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $ring.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $graphics.DrawLine(
    $ring,
    $lensX + $lensSize * 0.62,
    $lensY + $lensSize * 0.61,
    $lensX + $lensSize * 0.91,
    $lensY + $lensSize * 0.91
  )

  $bitmap.Save((Join-Path $iconsDirectory "icon-$size.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $ring.Dispose()
  $format.Dispose()
  $font.Dispose()
  $orange.Dispose()
  $white.Dispose()
  $navy.Dispose()
  $tile.Dispose()
  $graphics.Dispose()
  $bitmap.Dispose()
}

Write-Output "Generated A11yLens PNG icons in $iconsDirectory"
