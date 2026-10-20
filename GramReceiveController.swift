import UIKit
import CoreImage
import Display
import ComponentFlow
import TelegramPresentationData
import PremiumDiamondComponent

// The QR encodes an internal Blaxygram transfer address, never a username.
final class GramReceiveController: UIViewController {
    private let address: String
    private let theme: PresentationTheme
    private let topUp: () -> Void
    private let panel = UIView()
    private let gradient = CAGradientLayer()
    private let qr = UIImageView()
    private let ring = UIView()
    private let copyButton = UIButton(type: .system)
    private let closeButton = UIButton(type: .system)
    private let buyButton = UIButton(type: .system)
    private let gemButton = UIButton(type: .system)
    private let hint = UILabel()
    private let addressLabel = UILabel()
    private var diamond = ComponentView<Empty>()
    private var expanded = false
    private var lastRingSize = CGSize.zero

    init(address: String, theme: PresentationTheme, topUp: @escaping () -> Void) {
        self.address = address
        self.theme = theme
        self.topUp = topUp
        super.init(nibName: nil, bundle: nil)
        self.modalPresentationStyle = .overFullScreen
        self.modalTransitionStyle = .crossDissolve
    }

    required init?(coder: NSCoder) { return nil }

    override func viewDidLoad() {
        super.viewDidLoad()
        self.view.backgroundColor = UIColor.black.withAlphaComponent(0.45)
        self.panel.layer.cornerRadius = 32
        self.panel.clipsToBounds = true
        self.gradient.colors = [UIColor(rgb: 0x087bfa).cgColor, UIColor(rgb: 0x42baff).cgColor, UIColor(rgb: 0x087bfa).cgColor]
        self.panel.layer.insertSublayer(self.gradient, at: 0)
        self.view.addSubview(self.panel)
        self.ring.isUserInteractionEnabled = false
        self.panel.addSubview(self.ring)
        self.qr.backgroundColor = .white
        self.qr.layer.cornerRadius = 22
        self.qr.clipsToBounds = true
        self.qr.contentMode = .scaleAspectFit
        self.qr.layer.magnificationFilter = .nearest
        if let filter = CIFilter(name: "CIQRCodeGenerator") {
            filter.setValue(Data(("https://blaxygram.duckdns.org/mini/gram-link.html#" + self.address).utf8), forKey: "inputMessage")
            filter.setValue("H", forKey: "inputCorrectionLevel")
            if let output = filter.outputImage {
                let bordered = output.extent.insetBy(dx: -4, dy: -4)
                let white = CIImage(color: CIColor.white).cropped(to: bordered)
                let image = output.composited(over: white).transformed(by: CGAffineTransform(scaleX: 6, y: 6))
                if let cgImage = CIContext().createCGImage(image, from: image.extent) {
                    self.qr.image = UIImage(cgImage: cgImage)
                }
            }
        }
        self.panel.addSubview(self.qr)
        self.closeButton.setTitle("✕", for: .normal)
        self.closeButton.titleLabel?.font = .systemFont(ofSize: 24)
        self.closeButton.tintColor = .white
        self.closeButton.accessibilityLabel = "Закрыть"
        self.closeButton.addTarget(self, action: #selector(close), for: .touchUpInside)
        self.panel.addSubview(self.closeButton)
        self.copyButton.setTitle("Копировать мой адрес", for: .normal)
        self.copyButton.backgroundColor = .white
        self.copyButton.layer.cornerRadius = 18
        self.copyButton.addTarget(self, action: #selector(copyAddress), for: .touchUpInside)
        self.panel.addSubview(self.copyButton)
        self.buyButton.setTitle("Пополнить GRAM", for: .normal)
        self.buyButton.titleLabel?.font = .systemFont(ofSize: 19, weight: .semibold)
        self.buyButton.backgroundColor = .white
        self.buyButton.layer.cornerRadius = 26
        self.buyButton.addTarget(self, action: #selector(buy), for: .touchUpInside)
        self.panel.addSubview(self.buyButton)
        self.gemButton.setTitle("💎", for: .normal)
        self.gemButton.titleLabel?.font = .systemFont(ofSize: 27)
        self.gemButton.backgroundColor = .white
        self.gemButton.layer.cornerRadius = 12
        self.gemButton.accessibilityLabel = "Увеличить алмаз"
        self.gemButton.addTarget(self, action: #selector(toggleDiamond), for: .touchUpInside)
        self.panel.addSubview(self.gemButton)
        self.hint.text = "Чтобы получить GRAM, покажите QR или скопируйте адрес. Нажмите на алмаз — его можно вращать пальцем."
        self.hint.textColor = .white
        self.hint.textAlignment = .center
        self.hint.numberOfLines = 0
        self.hint.font = .systemFont(ofSize: 15)
        self.panel.addSubview(self.hint)
        self.addressLabel.text = self.address
        self.addressLabel.textColor = UIColor.white.withAlphaComponent(0.85)
        self.addressLabel.textAlignment = .center
        self.addressLabel.numberOfLines = 2
        self.addressLabel.font = .monospacedSystemFont(ofSize: 10, weight: .regular)
        self.panel.addSubview(self.addressLabel)
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let width = min(430, self.view.bounds.width - 16)
        let available = self.view.bounds.height - self.view.safeAreaInsets.top - self.view.safeAreaInsets.bottom - 20
        let side = min(width - 84, max(140, available - 295))
        let height = side + 295
        self.panel.frame = CGRect(x: (self.view.bounds.width - width) / 2, y: self.view.bounds.height - self.view.safeAreaInsets.bottom - height - 8, width: width, height: height)
        self.gradient.frame = self.panel.bounds
        self.closeButton.frame = CGRect(x: 12, y: 8, width: 44, height: 44)
        self.qr.frame = CGRect(x: (width - side) / 2, y: 68, width: side, height: side)
        self.ring.frame = self.qr.frame.insetBy(dx: -20, dy: -20)
        self.copyButton.frame = CGRect(x: 30, y: side + 97, width: width - 60, height: 38)
        self.addressLabel.frame = CGRect(x: 24, y: side + 140, width: width - 48, height: 28)
        self.hint.frame = CGRect(x: 26, y: side + 172, width: width - 52, height: 60)
        self.buyButton.frame = CGRect(x: 24, y: height - 57, width: width - 48, height: 48)
        self.gemButton.frame = CGRect(x: self.qr.center.x - 18, y: self.qr.center.y - 18, width: 36, height: 36)
        if self.expanded {
            let size = min(210, side * 0.83)
            _ = self.diamond.update(transition: .immediate, component: AnyComponent(PremiumDiamondComponent(theme: self.theme)), environment: {}, containerSize: CGSize(width: size, height: size))
            if let diamondView = self.diamond.view {
                if diamondView.superview == nil {
                    self.panel.addSubview(diamondView)
                    diamondView.addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(toggleDiamond)))
                    diamondView.accessibilityLabel = "Алмаз. Вращайте пальцем, нажмите для уменьшения"
                }
                diamondView.frame = CGRect(x: self.qr.center.x - size / 2, y: self.qr.center.y - size / 2, width: size, height: size)
            }
        }
        self.gemButton.isHidden = self.expanded
        if self.lastRingSize != self.ring.bounds.size {
            self.lastRingSize = self.ring.bounds.size
            self.buildRing()
        }
    }

    private func buildRing() {
        self.ring.layer.sublayers?.forEach { $0.removeFromSuperlayer() }
        let path = UIBezierPath(roundedRect: self.ring.bounds.insetBy(dx: 4, dy: 4), cornerRadius: 36)
        let text = Array(self.address + " · ")
        for (index, character) in text.enumerated() {
            let layer = CATextLayer()
            layer.string = String(character)
            layer.fontSize = 10
            layer.foregroundColor = UIColor(rgb: 0x0759a5).withAlphaComponent(0.8).cgColor
            layer.contentsScale = UIScreen.main.scale
            layer.bounds = CGRect(x: 0, y: 0, width: 10, height: 13)
            layer.alignmentMode = .center
            self.ring.layer.addSublayer(layer)
            let animation = CAKeyframeAnimation(keyPath: "position")
            animation.path = path.cgPath
            animation.calculationMode = .paced
            animation.rotationMode = .rotateAuto
            animation.duration = 24
            animation.repeatCount = .infinity
            animation.timeOffset = Double(index) / Double(text.count) * 24
            if UIAccessibility.isReduceMotionEnabled { animation.speed = 0 }
            layer.add(animation, forKey: "addressOrbit")
        }
    }

    @objc private func toggleDiamond() {
        self.expanded.toggle()
        if !self.expanded {
            self.diamond.view?.removeFromSuperview()
            self.diamond = ComponentView<Empty>()
        }
        self.view.setNeedsLayout()
    }
    @objc private func close() { self.dismiss(animated: true) }
    @objc private func copyAddress() {
        UIPasteboard.general.string = self.address
        self.copyButton.setTitle("Адрес скопирован ✓", for: .normal)
    }
    @objc private func buy() { self.dismiss(animated: true, completion: self.topUp) }
    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        self.ring.layer.sublayers?.forEach { $0.removeAllAnimations() }
        self.diamond.view?.removeFromSuperview()
        self.diamond = ComponentView<Empty>()
    }
}
