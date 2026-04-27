import 'dart:math' as math;

import 'package:flutter/material.dart';

class FairnessScaleAnimation extends StatefulWidget {
  const FairnessScaleAnimation({super.key});

  @override
  State<FairnessScaleAnimation> createState() => _FairnessScaleAnimationState();
}

class _FairnessScaleAnimationState extends State<FairnessScaleAnimation>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _angle;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _angle = Tween<double>(
      begin: -8 * math.pi / 180,
      end: 8 * math.pi / 180,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _angle,
      builder: (context, _) {
        return SizedBox(
          width: 80,
          height: 80,
          child: CustomPaint(
            painter: _FairnessScalePainter(
              angle: _angle.value,
              color: Theme.of(context).colorScheme.primary,
              accent: Theme.of(context).colorScheme.secondary,
              surface: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
          ),
        );
      },
    );
  }
}

class _FairnessScalePainter extends CustomPainter {
  const _FairnessScalePainter({
    required this.angle,
    required this.color,
    required this.accent,
    required this.surface,
  });

  final double angle;
  final Color color;
  final Color accent;
  final Color surface;

  @override
  void paint(Canvas canvas, Size size) {
    final basePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 3.2;

    final accentPaint = Paint()
      ..color = accent.withOpacity(0.22)
      ..style = PaintingStyle.fill;

    final panPaint = Paint()
      ..color = surface
      ..style = PaintingStyle.fill;

    final center = Offset(size.width / 2, size.height / 2);
    final standBottom = Offset(center.dx, size.height - 8);
    final standTop = Offset(center.dx, 24);

    canvas.drawCircle(center, size.width / 2.4, accentPaint);
    canvas.drawLine(standBottom, standTop, basePaint);
    canvas.drawLine(
      Offset(center.dx - 18, size.height - 8),
      Offset(center.dx + 18, size.height - 8),
      basePaint,
    );

    canvas.save();
    canvas.translate(center.dx, 22);
    canvas.rotate(angle);

    final beamHalf = size.width * 0.28;
    final leftAnchor = Offset(-beamHalf, 0);
    final rightAnchor = Offset(beamHalf, 0);
    canvas.drawLine(leftAnchor, rightAnchor, basePaint);
    canvas.drawCircle(Offset.zero, 3.5, Paint()..color = color);

    _drawPan(canvas, leftAnchor, basePaint, panPaint, accent, size.width * 0.18);
    _drawPan(canvas, rightAnchor, basePaint, panPaint, accent, size.width * 0.18);
    canvas.restore();
  }

  void _drawPan(
    Canvas canvas,
    Offset anchor,
    Paint strokePaint,
    Paint fillPaint,
    Color accentColor,
    double panWidth,
  ) {
    const ropeLength = 16.0;
    final leftRopeTop = anchor + const Offset(-8, 0);
    final rightRopeTop = anchor + const Offset(8, 0);
    final leftRopeBottom = leftRopeTop + const Offset(0, ropeLength);
    final rightRopeBottom = rightRopeTop + const Offset(0, ropeLength);
    final bowlRect = Rect.fromCenter(
      center: anchor + const Offset(0, ropeLength + 4),
      width: panWidth,
      height: 10,
    );

    canvas.drawLine(anchor, leftRopeTop, strokePaint);
    canvas.drawLine(anchor, rightRopeTop, strokePaint);
    canvas.drawLine(leftRopeTop, leftRopeBottom, strokePaint);
    canvas.drawLine(rightRopeTop, rightRopeBottom, strokePaint);
    canvas.drawArc(bowlRect, 0, math.pi, false, strokePaint);
    canvas.drawArc(
      bowlRect.deflate(1.6),
      0,
      math.pi,
      true,
      fillPaint..color = accentColor.withOpacity(0.12),
    );
  }

  @override
  bool shouldRepaint(covariant _FairnessScalePainter oldDelegate) {
    return oldDelegate.angle != angle ||
        oldDelegate.color != color ||
        oldDelegate.accent != accent ||
        oldDelegate.surface != surface;
  }
}
