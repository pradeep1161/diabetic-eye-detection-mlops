import os, argparse, sys, mlflow, mlflow.keras, numpy as np, tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetV2B0
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import accuracy_score

class EyeDiseaseModelTrainer:
    def __init__(self, config):
        self.config = config; self.img_size = (224, 224); self.batch_size = 32
        self.num_classes = len(config['classes']); self.model = None; self.base_model = None
    
    def prepare_data(self):
        """Prepares the data generators for training and validation."""
        train_datagen = ImageDataGenerator(
            rotation_range=20, width_shift_range=0.2, height_shift_range=0.2,
            horizontal_flip=True, zoom_range=0.2, shear_range=0.2,
            fill_mode='nearest',
            preprocessing_function=tf.keras.applications.efficientnet_v2.preprocess_input
        )
        val_datagen = ImageDataGenerator(
            preprocessing_function=tf.keras.applications.efficientnet_v2.preprocess_input
        )
        self.train_generator = train_datagen.flow_from_directory(
            os.path.join(self.config['dataset_path'], 'train'),
            target_size=self.img_size, batch_size=self.batch_size,
            class_mode='categorical', shuffle=True, classes=self.config['classes']
        )
        self.val_generator = val_datagen.flow_from_directory(
            os.path.join(self.config['dataset_path'], 'validation'),
            target_size=self.img_size, batch_size=self.batch_size,
            class_mode='categorical', shuffle=False, classes=self.config['classes']
        )

    def build_model(self):
        """Builds the EfficientNetV2B0 model."""
        self.base_model = EfficientNetV2B0(input_shape=(*self.img_size, 3), include_top=False, weights='imagenet')
        self.base_model.trainable = False
        inputs = tf.keras.Input(shape=(*self.img_size, 3))
        x = self.base_model(inputs, training=False)
        x = layers.GlobalAveragePooling2D()(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dense(256, activation='relu')(x)
        x = layers.Dropout(0.5)(x)
        outputs = layers.Dense(self.num_classes, activation='softmax')(x)
        self.model = models.Model(inputs, outputs)

    def train(self, epochs=25, fine_tune_epochs=15):
        """Trains, fine-tunes, and logs the model with MLflow."""
        mlflow.set_experiment(self.config['experiment_name'])
        with mlflow.start_run() as run:
            print(f"--- Starting MLflow Run: {run.info.run_id} ---")
            mlflow.log_params({"model_type": self.config['type'], "image_size": self.img_size[0], "batch_size": self.batch_size})
            
            # Initial Training
            self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])
            self.model.fit(self.train_generator, epochs=epochs, validation_data=self.val_generator, callbacks=[EarlyStopping(patience=10, restore_best_weights=True)], verbose=1)
            
            # Fine-Tuning
            self.base_model.trainable = True
            for layer in self.base_model.layers[:-30]: layer.trainable = False
            self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5), loss='categorical_crossentropy', metrics=['accuracy'])
            self.model.fit(self.train_generator, epochs=fine_tune_epochs, validation_data=self.val_generator, verbose=1)
            
            # Evaluation and Logging
            predictions = self.model.predict(self.val_generator)
            y_pred = np.argmax(predictions, axis=1)
            y_true = self.val_generator.classes
            accuracy = accuracy_score(y_true, y_pred)
            mlflow.log_metric("val_accuracy", accuracy)
            mlflow.keras.log_model(self.model, artifact_path="model", registered_model_name=self.config['registered_model_name'])
            print("--- MLflow Run Complete ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train an eye disease model.")
    parser.add_argument('--type', type=str, required=True, choices=['fundus', 'oct'])
    args = parser.parse_args()
    
    model_configs = {
        'fundus': {'type': 'fundus', 'dataset_path': '../dataset/fundus', 'experiment_name': 'Diabetic Eye - Fundus', 'registered_model_name': 'fundus-model', 'classes': ['normal', 'diabetic_retinopathy', 'cataracts', 'glaucoma']},
        'oct': {'type': 'oct', 'dataset_path': '../dataset/oct', 'experiment_name': 'Diabetic Eye - OCT', 'registered_model_name': 'oct-model', 'classes': ['normal', 'macular_edema']}
    }
    config = model_configs[args.type]

    # --- NEW: Simplified Data Check ---
    train_path = os.path.join(config['dataset_path'], 'train')
    validation_path = os.path.join(config['dataset_path'], 'validation')

    if not os.path.exists(train_path) or not os.path.exists(validation_path):
        print(f"FATAL ERROR: Data directory not found.")
        print(f"Checked for training data at: {os.path.abspath(train_path)}")
        print(f"Checked for validation data at: {os.path.abspath(validation_path)}")
        print("This error in a CI/CD environment usually means the 'dvc pull' step failed or was not configured correctly.")
        sys.exit(1)

    print(f"✅ Data directories found. Proceeding with training for model type: {args.type.upper()}")
    trainer = EyeDiseaseModelTrainer(config)
    trainer.prepare_data()
    trainer.build_model()
    trainer.train()
