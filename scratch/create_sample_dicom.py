import os
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
import datetime

def crear_corte_dicom(filename, shape=(64, 64), z_pos=0.0):
    file_meta = pydicom.dataset.FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.PatientName = "Test^Patient"
    ds.PatientID = "123456"
    ds.Modality = "CT"
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime('%Y%m%d')
    ds.ContentTime = dt.strftime('%H%M%S')

    ds.Rows = shape[0]
    ds.Columns = shape[1]
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelSpacing = ["1.0", "1.0"]
    ds.SliceThickness = "1.0"
    ds.ImagePositionPatient = ["0.0", "0.0", str(z_pos)]
    ds.RescaleSlope = "1"
    ds.RescaleIntercept = "-1000"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1

    # Create dummy volume data (cylinder/sphere shape with bone density)
    grid_y, grid_x = np.ogrid[:shape[0], :shape[1]]
    dist_from_center = np.sqrt((grid_y - shape[0]/2)**2 + (grid_x - shape[1]/2)**2)
    slice_data = np.zeros(shape, dtype=np.int16)
    slice_data[dist_from_center < 20] = 1000  # soft tissue HU + intercept offset
    slice_data[dist_from_center < 10] = 2000  # bone HU + intercept offset

    ds.PixelData = slice_data.tobytes()
    ds.save_as(filename)

def main():
    os.makedirs("data/raw/sample_study", exist_ok=True)
    for i in range(5):
        filepath = f"data/raw/sample_study/slice_{i:02d}.dcm"
        crear_corte_dicom(filepath, z_pos=float(i * 2.0))
    print("Muestra DICOM sintética creada exitosamente en data/raw/sample_study/")

if __name__ == "__main__":
    main()
