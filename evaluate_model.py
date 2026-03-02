import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# Load the log
df = pd.read_csv("recognition_log.csv")

# Filter out invalid rows
df.dropna(inplace=True)

# Ground truth and prediction
y_true = df["ground_truth"]
y_pred = df["predicted"]

# Report
print("Classification Report:\n")
print(classification_report(y_true, y_pred))

# Save report
report_df = pd.DataFrame(classification_report(y_true, y_pred, output_dict=True)).transpose()
report_df.to_csv("classification_report.csv", index=True)

# Confusion Matrix
cm = confusion_matrix(y_true, y_pred)
plt.figure(figsize=(6,5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=sorted(set(y_true)), yticklabels=sorted(set(y_true)))
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.savefig("confusion_matrix_face_recognition.jpeg")
plt.show()


import pandas as pd
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt

# Load your recognition log
df = pd.read_csv("recognition_log.csv")


y_true = df["ground_truth"]
y_pred = df["predicted"]

# Generate classification report as a dict
report = classification_report(y_true, y_pred, output_dict=True)

# Exclude avg/total rows
classes = [label for label in report if label not in ['accuracy', 'macro avg', 'weighted avg']]

# Prepare data for plotting
precision = [report[cls]["precision"] for cls in classes]
recall = [report[cls]["recall"] for cls in classes]
f1 = [report[cls]["f1-score"] for cls in classes]

# Create bar chart
x = range(len(classes))
width = 0.25

plt.figure(figsize=(10, 6))
plt.bar([i - width for i in x], precision, width=width, label="Precision", color='skyblue')
plt.bar(x, recall, width=width, label="Recall", color='orange')
plt.bar([i + width for i in x], f1, width=width, label="F1-Score", color='green')

plt.xticks(x, classes)
plt.ylabel("Score")
plt.ylim(0, 1.05)
plt.title("Precision, Recall, and F1-Score for Face Recognition")
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Save the figure
plt.tight_layout()
plt.savefig("classification_metrics_face_recognition.jpeg")
plt.show()
