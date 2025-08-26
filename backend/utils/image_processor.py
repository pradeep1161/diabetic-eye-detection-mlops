import cv2
import numpy as np
import tensorflow as tf
import base64

class ImageProcessor:
    def __init__(self):
        self.target_size = (224, 224)
    
    def preprocess_fundus(self, image_path):
        img = cv2.imread(image_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        final_img = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
        resized_img = cv2.resize(final_img, self.target_size)
        return np.array(resized_img, dtype=np.uint8)
    
    def enhance_oct(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        img_denoised = cv2.fastNlMeansDenoising(img, None, 10, 7, 21)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_enhanced = clahe.apply(img_denoised)
        img_rgb = cv2.cvtColor(img_enhanced, cv2.COLOR_GRAY2RGB)
        resized_img = cv2.resize(img_rgb, self.target_size)
        return np.array(resized_img, dtype=np.uint8)

    def generate_grad_cam(self, model, img_array, last_conv_layer_name):
        """Generates a Grad-CAM heatmap and returns it as a Base64 string."""
        img_batch = np.expand_dims(img_array, axis=0)
        preprocessed_img = tf.keras.applications.efficientnet_v2.preprocess_input(img_batch)

        grad_model = tf.keras.models.Model(
            model.inputs, [model.get_layer(last_conv_layer_name).output, model.output]
        )

        with tf.GradientTape() as tape:
            last_conv_layer_output, preds = grad_model(preprocessed_img)
            pred_index = tf.argmax(preds[0])
            class_channel = preds[:, pred_index]

        grads = tape.gradient(class_channel, last_conv_layer_output)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        last_conv_layer_output = last_conv_layer_output[0]
        heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        heatmap = heatmap.numpy()

        heatmap = cv2.resize(heatmap, (img_array.shape[1], img_array.shape[0]))
        heatmap = np.uint8(255 * heatmap)
        heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        superimposed_img = cv2.addWeighted(img_array, 0.6, heatmap, 0.4, 0)
        
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(superimposed_img, cv2.COLOR_RGB2BGR))
        heatmap_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return heatmap_b64
