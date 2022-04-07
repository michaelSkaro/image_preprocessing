# we need to break down the IntersectPolygons method into smaller functions. I am experiencing too many bugs

# the objective today will be to break the method into 5 parts
    # 1. Read in the annotation data and return a list of dictionaries
    # 2. Pass the list of dictionaries to a readIMage function, read in an image from the filename key
    # 3. Padd the image and tile the image. Return a list of coordinates for the bounding boxes
    # 4. Iterate over each of the segmentations in the image and intersect them with the tile bounding boxes
    # 5. If the segmentation intersects the tile, add it to a list of objects
    # 6. Iterate over the list of objects and add them to the dataset_dicts

def convertPoints(anno):
    points = [[]]
                    
    for x_coordinate in range(0,len(anno["all_points_x"]),2):
        points.append([anno["all_points_x"][x_coordinate],anno["all_points_y"][x_coordinate]])
    
    # remove empyt lists from the list of points
    points = [x for x in points if x]
    
    return points



def intersectBoundingBox(points,xmin,ymin,xmax,ymax):
    converted_points = []

    for p in points:
        if p[0]>=xmin and p[0]<=xmax and p[1]>=ymin and p[1]<=ymax:
            p[0]=p[0]-xmin
            p[1]=p[1]-ymin
            converted_points.append(p)
    
    #print(converted_points)

    return converted_points



def readAnnotation(img_dir):
    '''
    :param img_dir:
    :return list of dictionaries:

    '''
    anno_file=os.path.join(img_dir,"regiondata.csv")
    annotab=pd.read_csv(anno_file,delimiter=",")
    files=annotab['filename'].unique()



    return annotab, files

def readImage(img_dir,filename):
    '''
    :param img_dir:
    :param filename:
    :return image:
    '''
    img_file=os.path.join(img_dir,filename)
    img=cv2.imread(img_file)
    height = img.shape[0]
    width = img.shape[1]
    
    # padd the image to be divisible by 512
    # padd the image
    pad_h=(512 - (height % 512)) % 512
    pad_w=(512 - (width % 512)) % 512
    # pad the image
    img=cv2.copyMakeBorder(img,0,pad_h,0,pad_w,cv2.BORDER_CONSTANT,value=[0,0,0])



    return img

def tileImage(img):
    '''
    :param img:
    :return list of coordinates:
    :rtype list:

    Objective: output a list of coordinates for the bounding boxes of the tiles

    '''
    tiles=[[]]
    for i in range(0,img.shape[0],512):
            for j in range(0,img.shape[1],512):
                #print(i,j)
                tile=img[i:i+512,j:j+512]
                xmin=j
                ymin=i
                xmax=j+512
                ymax=i+512
                tiles[0].append([xmin,ymin,xmax,ymax])
                

    return tiles

def IntersectSegmentations(img_dir,output_dir, tiles, img, annotab, file):
    '''
    :param tiles:
    :paramtype list:
    :param img:
    :paramtype numpy array:
    :param annotab:
    :paramtype pandas dataframe:
    :param files:
    :paramtype list:
    :return dataset_dicts:
    :rtype list:

    Objective: iterate over each of the segmentations in the image and intersect them with the tile bounding boxes
    '''
    filename=os.path.join(img_dir,file)
    records=[]
    # iterate over the tile coordinates
    for tile in tiles[0]:
        record = {}
        
        # get the coordinate over the tile image
        xmin=tile[0]
        ymin=tile[1]
        xmax=tile[2]
        ymax=tile[3]
        
        #print(xmin,ymin,xmax,ymax)
        #subset the image to the tile coordinates
        subimg=img[xmin:xmax,ymin:ymax]

        # make a tile id using the UUID
        uid = str(uuid.uuid4())

        # write the image tile to a file using the UID as the name
        

        

        # begin building the record by adding the information for the COCO dataset
        record["filename"] = uid + '.jpg'
        record["height"] = 512
        record["width"] = 512
        # make an empty list of objects for record annotation
        record["annotations"] = []
        
        subtab = annotab[annotab['filename'] == file]
        objs =[]
        for anno_i in range(subtab.shape[0]):
            
            tab_rec=subtab.iloc[anno_i]
            
            # get the catagory id
            category_id=classes.index(tab_rec['region_attributes'])
            # convert the category id to the class name by using the classes array
            className=classes[category_id]
            anno=json.loads(tab_rec["region_shape_attributes"])
            if len(anno)==0:
                continue
            #print(anno)

            points=convertPoints(anno)
            # this is the problem line
            converted_points=intersectBoundingBox(points,xmin,ymin,xmax,ymax)
            
            if len(converted_points) > 1:
                
                Sxmin=min(converted_points,key=lambda x:x[0])[0]
                Symin=min(converted_points,key=lambda x:x[1])[1]
                Sxmax=max(converted_points,key=lambda x:x[0])[0]
                Symax=max(converted_points,key=lambda x:x[1])[1]
                converted_points=[item for sublist in converted_points for item in sublist]
                Segbbox = [Sxmin,Symin,Sxmax,Symax]

                obj = {
                    'original_file': filename,
                    "tile_coordinates": [xmin,ymin,xmax,ymax],
                    "image_id": uid,
                    'file_name': uid + '.jpg',
                    'height': 512,
                    'width': 512,
                    "category_id": className,
                    "bbox": Segbbox,
                    "segmentation": converted_points,
                    "bbox_mode": 'BoxMode.XYXY_ABS',
                    "iscrowd":0,
                    }
                objs.append(obj)
                # append the object to the list of objects 

        record["annotations"] = objs
        records.append(record)
        # if the img is not empty, then write the image to a file
        if len(subimg)>0:
            cv2.imwrite(os.path.join(output_dir,uid + '.jpg'),subimg)

    return records

 
def writeRegionDataSet(dataset_dicts):
    '''
    :param dataset_dicts:
    :return:
    
    # Objective: Iterate over the dataset_dicts, each record will consist of filename, image_id, height, width, and annotations.
    We want to iterate over the annotations and write each annotation to a line in the csv file where the header line of the file
    will be the keys of the annotations dict.
    '''
    import csv
    with open(output_dir+"regiondata.csv", "w") as csvfile:
        
        fieldnames = ['original_file', 'tile_coordinates', 'image_id', 'file_name', 'height', 'width', 'category_id' , 
        'bbox', 'segmentation', 'bbox_mode', 'iscrowd']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in dataset_dicts:
            for obj in record["annotations"]:
                writer.writerow(obj)   
    
    pass
    
             
     
#img = readImage(img_dir,files[0])
#iles = tileImage(img)
#IntersectSegmentations(img_dir,output_dir, tiles, img, annotab, files[0])
# RUNNER
annotab, files = readAnnotation(img_dir)
dataset_dicts = []
for stained_image in files:
    img = readImage(img_dir,stained_image)
    tiles = tileImage(img)
    record = IntersectSegmentations(img_dir,output_dir, tiles, img, annotab, stained_image)
    dataset_dicts.extend(record)


writeRegionDataSet(dataset_dicts)
    









